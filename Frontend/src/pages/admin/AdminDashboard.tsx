import {
  Server,
  CheckCircle2,
  Clock,
  AlertTriangle,
  TrendingUp,
  Activity,
} from "lucide-react";
import MetricCard from "@/components/admin/MetricCard";
import RequestsChart from "@/components/admin/RequestsChart";
import RecentActivity from "@/components/admin/RecentActivity";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import {
  useErrorDistribution,
  useMetricsOverview,
  useRecentRequests,
  useRequestsChart,
  useSystemStatus,
} from "@/api/hooks";
import QueryError from "@/components/QueryError";
import { cn } from "@/lib/utils";

const AdminDashboard = () => {
  const overviewQuery = useMetricsOverview();
  const chartQuery = useRequestsChart(7);
  const errorsQuery = useErrorDistribution();
  const recentQuery = useRecentRequests(10);
  const statusQuery = useSystemStatus();

  const overview = overviewQuery.data;
  const chartData = chartQuery.data ?? [];
  const errorDistribution = errorsQuery.data;
  const recentRequests = recentQuery.data ?? [];
  const systemStatus = statusQuery.data;
  const failed = [overviewQuery, chartQuery, errorsQuery, recentQuery, statusQuery].find(
    (query) => query.isError,
  );

  const errorChartData = errorDistribution
    ? [
        { name: "Timeout", value: errorDistribution.timeout, color: "hsl(var(--destructive))" },
        { name: "Erreur LLM", value: errorDistribution.llm_error, color: "hsl(var(--warning))" },
        { name: "Retrieval", value: errorDistribution.retrieval, color: "hsl(var(--chart-3))" },
        { name: "Web Search", value: errorDistribution.web_search, color: "hsl(var(--chart-4))" },
        { name: "Autres", value: errorDistribution.other, color: "hsl(var(--muted-foreground))" },
      ]
    : [];

  const healthy = systemStatus
    ? systemStatus.rag_pipeline === "Active" &&
      systemStatus.vector_db === "Connected" &&
      systemStatus.llm_status === "Operational"
    : null;
  const overall =
    healthy === null
      ? { dot: "bg-muted-foreground", label: "Vérification…" }
      : healthy
        ? { dot: "bg-success", label: "Opérationnel" }
        : systemStatus?.llm_status === "Down" || systemStatus?.vector_db === "Disconnected"
          ? { dot: "bg-destructive", label: "Incident" }
          : { dot: "bg-warning", label: "Dégradé" };
  const tone = (ok: boolean) => (systemStatus ? (ok ? "text-success" : "text-destructive") : "text-muted-foreground");

  const successRate = overview ? `${overview.success_rate.toFixed(1)}%` : "--";
  const averageLatency = overview ? `${overview.average_latency.toFixed(2)}s` : "--";

  return (
    <div className="space-y-6 relative">
      {/* Header with gradient effect */}
      <div className="relative">
        <div className="absolute inset-0 bg-linear-to-r from-primary/5 via-transparent to-transparent blur-3xl opacity-50" />
        <div className="relative flex flex-col gap-1">
          <h1 className="text-4xl md:text-5xl font-oswald font-medium tracking-tight">
            Dashboard
          </h1>
          <p className="text-muted-foreground text-lg">
            Vue d'ensemble des performances du système RAG
          </p>
        </div>
      </div>

      {failed && (
        <QueryError
          error={failed.error}
          onRetry={() => {
            for (const query of [overviewQuery, chartQuery, errorsQuery, recentQuery, statusQuery]) {
              if (query.isError) void query.refetch();
            }
          }}
        />
      )}

      {/* Metrics Grid with enhanced cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Requêtes"
          value={overview ? overview.total_requests.toLocaleString() : "--"}
          subtitle="Toutes les requêtes"
          icon={Server}
        />
        <MetricCard
          title="Requêtes Aujourd'hui"
          value={overview ? overview.requests_today.toString() : "--"}
          subtitle="Depuis minuit"
          icon={Activity}
          variant="success"
        />
        <MetricCard
          title="Taux de Succès"
          value={successRate}
          subtitle={overview ? `${overview.error_count} échecs` : "—"}
          icon={CheckCircle2}
          variant="success"
        />
        <MetricCard
          title="Latence Moyenne"
          value={averageLatency}
          subtitle="End-to-end"
          icon={Clock}
          variant="warning"
        />
      </div>

      {/* Charts Row with enhanced styling */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <RequestsChart data={chartData} />
        </div>
        
        {/* Error Distribution with enhanced card */}
        <Card className="relative overflow-hidden border-border/50 hover:border-primary/30 transition-all duration-300 hover:shadow-lg hover:shadow-primary/5">
          <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full blur-2xl" />
          <CardHeader className="pb-2 relative z-10">
            <CardTitle className="text-lg font-oswald">Répartition des erreurs</CardTitle>
          </CardHeader>
          <CardContent className="relative z-10">
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={errorChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {errorChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      borderColor: "hsl(var(--border))",
                      borderRadius: "8px",
                      boxShadow: "0 4px 20px -2px hsl(var(--foreground) / 0.08)",
                    }}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: "12px" }}
                    formatter={(value) => (
                      <span style={{ color: "hsl(var(--foreground))" }}>{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity with enhanced styling */}
      <div className="relative">
        <RecentActivity requests={recentRequests} />
      </div>

      {/* System Status with template-inspired design */}
      <Card className="relative overflow-hidden bg-linear-to-br from-foreground to-foreground/95 text-background border-0 shadow-xl">
        <div className="absolute inset-0 noise-overlay" />
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary/20 rounded-full blur-3xl" />
        <CardContent className="p-6 relative z-10">
          <div className="flex items-center justify-between mb-6">
            <div>
              <span className="text-xs font-space uppercase tracking-widest text-primary mb-2 block">
                État du Système
              </span>
              <h3 className="text-xl font-oswald font-medium">Statut en temps réel</h3>
            </div>
            <div className="flex items-center gap-2" role="status">
              <span className={cn("w-2 h-2 rounded-full animate-pulse", overall.dot)} />
              <span className="text-sm font-medium">{overall.label}</span>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-sm">
            <div className="flex justify-between items-center p-3 rounded-lg bg-background/10 backdrop-blur-xs border border-background/20">
              <span className="text-muted-foreground">&gt; RAG Pipeline</span>
              <span className={cn("font-semibold", tone(systemStatus?.rag_pipeline === "Active"))}>
                {systemStatus ? `${systemStatus.rag_pipeline} · ${systemStatus.documents_ready} doc.` : "—"}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-background/10 backdrop-blur-xs border border-background/20">
              <span className="text-muted-foreground">&gt; Vector DB</span>
              <span className={cn("font-semibold", tone(systemStatus?.vector_db === "Connected"))}>
                {systemStatus?.vector_db ?? "—"}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-background/10 backdrop-blur-xs border border-background/20">
              <span className="text-muted-foreground">&gt; LLM</span>
              <span
                className={cn(
                  "font-semibold",
                  systemStatus?.llm_status === "Degraded" ? "text-warning" : tone(systemStatus?.llm_status === "Operational"),
                )}
              >
                {systemStatus
                  ? `${systemStatus.llm_status}${systemStatus.availability_24h != null ? ` · ${systemStatus.availability_24h}% (24 h)` : ""}`
                  : "—"}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Performance Insights */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="relative overflow-hidden border-border/50 hover:border-primary/30 transition-all duration-300">
          <div className="absolute top-0 right-0 w-24 h-24 bg-success/10 rounded-full blur-2xl" />
          <CardHeader className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-5 h-5 text-success" />
              <CardTitle className="text-lg font-oswald">Tendances</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="relative z-10">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Croissance hebdomadaire</span>
                <span className="text-lg font-oswald font-medium text-success">+12.5%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Utilisateurs actifs</span>
                <span className="text-lg font-oswald font-medium">+8.2%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Satisfaction moyenne</span>
                <span className="text-lg font-oswald font-medium text-success">4.8/5</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-border/50 hover:border-primary/30 transition-all duration-300">
          <div className="absolute top-0 right-0 w-24 h-24 bg-warning/10 rounded-full blur-2xl" />
          <CardHeader className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-5 h-5 text-warning" />
              <CardTitle className="text-lg font-oswald">Alertes</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="relative z-10">
            <div className="space-y-3">
              <div className="flex items-start gap-3 p-3 rounded-lg bg-warning/5 border border-warning/20">
                <AlertTriangle className="w-4 h-4 text-warning shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Latence P95 élevée</p>
                  <p className="text-xs text-muted-foreground mt-1">4.2s (seuil: 3.5s)</p>
                </div>
              </div>
              <div className="text-sm text-muted-foreground text-center py-2">
                Aucune autre alerte active
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AdminDashboard;
