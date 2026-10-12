import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, Clock, Database, Search } from "lucide-react";
import MetricCard from "@/components/admin/MetricCard";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
} from "recharts";
import { useLatencyComponents, useLatencyTrend } from "@/api/hooks";
import QueryError from "@/components/QueryError";

const AdminMetrics = () => {
  const componentsQuery = useLatencyComponents();
  const trendQuery = useLatencyTrend(7);
  const latencyData = useMemo(() => componentsQuery.data ?? [], [componentsQuery.data]);
  const latencyTrend = trendQuery.data ?? [];
  const failed = [componentsQuery, trendQuery].find((query) => query.isError);

  const endToEndStats = useMemo(
    () => latencyData.find((item) => item.name === "End-to-End"),
    [latencyData]
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-oswald font-medium tracking-tight">
          Métriques & Performance
        </h1>
        <p className="text-muted-foreground">
          Analyse détaillée des latences et performances du système
        </p>
      </div>

      {failed && <QueryError error={failed.error} onRetry={() => void failed.refetch()} />}

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          title="Latence Moyenne"
          value={endToEndStats ? `${endToEndStats.avg.toFixed(2)}s` : "--"}
          subtitle="End-to-end"
          icon={Clock}
        />
        <MetricCard
          title="P95 Latence"
          value={endToEndStats ? `${endToEndStats.p95.toFixed(2)}s` : "--"}
          subtitle="95e percentile"
          icon={Activity}
          variant="warning"
        />
        <MetricCard
          title="Precision@5"
          value="—"
          subtitle="Non disponible"
          icon={Database}
          variant="success"
        />
        <MetricCard
          title="MAP Score"
          value="—"
          subtitle="Non disponible"
          icon={Search}
          variant="success"
        />
      </div>

      {/* Latency by Component */}
      <Card>
        <CardHeader>
          <CardTitle>Latence par composant</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={latencyData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  type="number"
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                  width={100}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    borderColor: "hsl(var(--border))",
                    borderRadius: "8px",
                  }}
                />
                <Legend />
                <Bar dataKey="avg" name="Moyenne" fill="hsl(var(--primary))" radius={4} />
                <Bar dataKey="p95" name="P95" fill="hsl(var(--warning))" radius={4} />
                <Bar dataKey="p99" name="P99" fill="hsl(var(--destructive))" radius={4} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Latency Trend */}
      <Card>
        <CardHeader>
          <CardTitle>Évolution des latences (7 jours)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={latencyTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                />
                <YAxis
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    borderColor: "hsl(var(--border))",
                    borderRadius: "8px",
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="endToEnd"
                  name="End-to-End"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="retrieval"
                  name="Retrieval"
                  stroke="hsl(var(--success))"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="generation"
                  name="Generation"
                  stroke="hsl(var(--chart-3))"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminMetrics;
