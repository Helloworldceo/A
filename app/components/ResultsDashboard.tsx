import type { AnalysisResult } from "@/app/lib/types";
import SummaryCard from "./SummaryCard";
import PVESSCard from "./PVESSCard";
import FinancialCard from "./FinancialCard";
import MonteCarloCard from "./MonteCarloCard";
import AIAnalysisCard from "./AIAnalysisCard";
import ReportView from "./ReportView";

export default function ResultsDashboard({ result }: { result: AnalysisResult }) {
  return (
    <div className="flex flex-col gap-6">
      <SummaryCard
        feasibility={result.feasibility_result}
        scenario={result.scenario_result}
        financial={result.financial_result}
      />
      <PVESSCard scenario={result.scenario_result} load={result.load_data} pv={result.pv_system_data} />
      <FinancialCard financial={result.financial_result} />
      <MonteCarloCard mc={result.montecarlo_result} />
      <AIAnalysisCard ai={result.ai_analysis} />
      <ReportView markdown={result.markdown_report} />
    </div>
  );
}
