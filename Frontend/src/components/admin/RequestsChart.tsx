import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface RequestsChartProps {
  data: { date: string; requests: number; success: number; errors: number }[];
}

const RequestsChart = ({ data }: RequestsChartProps) => {
  return (
    <Card className="relative overflow-hidden border-border/50 hover:border-primary/30 transition-all duration-300">
      {/* Background gradient effect */}
      <div className="absolute top-0 right-0 w-40 h-40 bg-primary/5 rounded-full blur-3xl" />
      
      <CardHeader className="pb-2 relative z-10">
        <CardTitle className="text-lg font-oswald">Requêtes par jour</CardTitle>
        <p className="text-sm text-muted-foreground mt-1">Évolution sur 7 jours</p>
      </CardHeader>
      <CardContent className="relative z-10">
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorRequests" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorSuccess" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--success))" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="hsl(var(--success))" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorErrors" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--destructive))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--destructive))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid 
                strokeDasharray="3 3" 
                stroke="hsl(var(--border))" 
                opacity={0.3}
              />
              <XAxis
                dataKey="date"
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                axisLine={{ stroke: "hsl(var(--border))", opacity: 0.5 }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                axisLine={{ stroke: "hsl(var(--border))", opacity: 0.5 }}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  borderColor: "hsl(var(--border))",
                  borderRadius: "8px",
                  boxShadow: "0 4px 20px -2px hsl(var(--foreground) / 0.08)",
                }}
                labelStyle={{ 
                  color: "hsl(var(--foreground))",
                  fontWeight: 600,
                  marginBottom: "4px"
                }}
                itemStyle={{ 
                  color: "hsl(var(--foreground))",
                  padding: "2px 0"
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: "12px", paddingTop: "20px" }}
                iconType="circle"
                formatter={(value) => (
                  <span style={{ color: "hsl(var(--foreground))" }}>{value}</span>
                )}
              />
              <Area
                type="monotone"
                dataKey="requests"
                stroke="hsl(var(--primary))"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#colorRequests)"
                name="Total"
              />
              <Area
                type="monotone"
                dataKey="success"
                stroke="hsl(var(--success))"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorSuccess)"
                name="Succès"
              />
              <Area
                type="monotone"
                dataKey="errors"
                stroke="hsl(var(--destructive))"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorErrors)"
                name="Erreurs"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

export default RequestsChart;
