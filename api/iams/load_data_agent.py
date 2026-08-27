from base_agent import BaseAgent, LoadData, UserInputs
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import os
import re

_SYSTEM_PROMPT = """Task: Parse the load data into a 24-hour array.

【Output Format】
Strictly output JSON:
{"load_data": [ number, number, ..., number ]}
- The array length must be 24
- Array index corresponds to the hourly interval:
  - 0th element → 0:00-1:00
  - 1st element → 1:00-2:00
  - 2nd element → 2:00-3:00
  - 3rd element → 3:00-4:00
  - 4th element → 4:00-5:00
  - 5th element → 5:00-6:00
  - 6th element → 6:00-7:00
  - 7th element → 7:00-8:00
  - 8th element → 8:00-9:00
  - 9th element → 9:00-10:00
  - 10th element → 10:00-11:00
  - 11th element → 11:00-12:00
  - 12th element → 12:00-13:00
  - 13th element → 13:00-14:00
  - 14th element → 14:00-15:00
  - 15th element → 15:00-16:00
  - 16th element → 16:00-17:00
  - 17th element → 17:00-18:00
  - 18th element → 18:00-19:00
  - 19th element → 19:00-20:00
  - 20th element → 20:00-21:00
  - 21st element → 21:00-22:00
  - 22nd element → 22:00-23:00
  - 23rd element → 23:00-0:00
- Do not output any text or extra content

【Parsing Rules】
1. Hours not mentioned default to 0.
2. "From x o'clock to n o'clock" follows left-closed, right-open interval:
   - Includes the starting hour, does not include the ending hour
   - Automatically handles crossing midnight
   - Examples:
     - "23:00 to 2:00 700kW" → elements 23, 0, 1 = 700
     - "5:00 to 7:00 1200kW" → elements 5, 6 = 1200
3. Single time points (e.g., "12:00 1000kW") → element 12 = 1000
4. Supports multiple time expressions: morning/afternoon/noon/early morning/midnight etc. → automatically converted to 24-hour time
5. If the same hour appears repeatedly, the last value overrides
6. Ignore unit differences (kw/kW/KW all the same)
7. Must self-check before output:
   - Array length = 24
   - The nth element strictly corresponds to n:00 to n+1:00 (23 loops to 0)
   - Left-closed, right-open interval strictly applied

【Examples】
Input: 11 PM to 2 AM 700kW, 9 AM to 12 PM 1200kW, 3 PM 1000kW
Output: {"load_data": [700,700,0,0,0,0,0,0,0,1200,1200,1200,0,0,0,1000,0,0,0,0,0,0,0,700]}

Input: 5:00 to 7:00 1200kW, 12:00 1000kW, 15:00 to 18:00 900kW
Output: {"load_data": [0,0,0,0,0,1200,1200,0,0,0,0,0,1000,0,0,900,900,900,0,0,0,0,0,0]}"""


class LoadExtractionAgent(BaseAgent):
    def __init__(self):
        super().__init__("Load Data Extraction Agent")
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
        )

    def _parse_time_token(self, token: str) -> int:
        text = (token or "").strip().lower().replace("o'clock", "")
        text = re.sub(r"\s+", " ", text)
        match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
        if not match:
            raise ValueError(f"Unsupported time token: {token}")

        hour = int(match.group(1))
        meridiem = match.group(3)
        if meridiem == "am":
            hour = 0 if hour == 12 else hour
        elif meridiem == "pm":
            hour = 12 if hour == 12 else hour + 12

        return hour % 24

    def _apply_range(self, hourly_load: list[float], start_hour: int, end_hour: int, value: float) -> None:
        hour = start_hour
        while True:
            hourly_load[hour] = value
            hour = (hour + 1) % 24
            if hour == end_hour:
                break

    def _rule_based_parse(self, raw_text: str) -> list[float]:
        hourly_load = [0.0] * 24
        parts = [part.strip() for part in re.split(r"[,;\n]+", raw_text) if part.strip()]
        if not parts:
            raise ValueError("No load segments found")

        range_pattern = re.compile(
            r"(?P<start>\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*(?:to|-|–)\s*"
            r"(?P<end>\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*"
            r"(?P<load>\d+(?:\.\d+)?)\s*k?w",
            re.IGNORECASE,
        )
        point_pattern = re.compile(
            r"(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*"
            r"(?P<load>\d+(?:\.\d+)?)\s*k?w",
            re.IGNORECASE,
        )

        parsed_any = False
        for part in parts:
            range_match = range_pattern.search(part)
            if range_match:
                start_hour = self._parse_time_token(range_match.group("start"))
                end_hour = self._parse_time_token(range_match.group("end"))
                value = float(range_match.group("load"))
                self._apply_range(hourly_load, start_hour, end_hour, value)
                parsed_any = True
                continue

            point_match = point_pattern.search(part)
            if point_match:
                hour = self._parse_time_token(point_match.group("time"))
                hourly_load[hour] = float(point_match.group("load"))
                parsed_any = True

        if not parsed_any:
            raise ValueError("Rule-based parser could not interpret load description")

        return hourly_load

    def run(self, validated_inputs: UserInputs) -> LoadData:
        """Extract and validate 24-hour load data"""
        self.log("Starting load data extraction")

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=validated_inputs.load_information)
        ]

        for attempt in range(self.max_retries):
            try:
                response = self.llm.invoke(messages)
                content = response.content.strip()
                # Strip markdown fences if present
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                content = content.strip()

                load_json = json.loads(content)
                # Support both key names: "load_data" (new) and "hourly_load" (old)
                hourly_load = load_json.get("load_data") or load_json.get("hourly_load")

                load_data = self.validate_schema({
                    "hourly_load": hourly_load,
                    "total_daily_load": sum(hourly_load),
                    "max_hourly_load": max(hourly_load) if hourly_load else 0
                }, LoadData)

                self.log(f"Successfully extracted load data: total {load_data.total_daily_load} kW, max {load_data.max_hourly_load} kW")
                return load_data

            except Exception as e:
                self.log(f"Extraction attempt {attempt+1} failed: {str(e)}", "WARNING")
                if attempt == self.max_retries - 1:
                    self.log("Max retries reached, switching to rule-based parser", "WARNING")

        try:
            hourly_load = self._rule_based_parse(validated_inputs.load_information)
            load_data = self.validate_schema({
                "hourly_load": hourly_load,
                "total_daily_load": sum(hourly_load),
                "max_hourly_load": max(hourly_load) if hourly_load else 0,
            }, LoadData)
            self.log(
                f"Rule-based extraction succeeded: total {load_data.total_daily_load} kW, "
                f"max {load_data.max_hourly_load} kW"
            )
            return load_data
        except Exception as fallback_error:
            self.log(f"Rule-based extraction failed: {str(fallback_error)}", "ERROR")
            raise ValueError(f"Failed to extract load data: {str(fallback_error)}")
