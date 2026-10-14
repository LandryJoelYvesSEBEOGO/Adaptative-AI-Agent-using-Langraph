import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, Filter, Download, Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import { useRequestDetails } from "@/api/hooks";
import QueryError from "@/components/QueryError";

const AdminApiRequests = () => {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const requestsQuery = useRequestDetails(100);
  const requests = useMemo(() => requestsQuery.data ?? [], [requestsQuery.data]);

  const filteredRequests = useMemo(() => {
    return requests.filter((req) => {
      const matchesStatus = statusFilter === "all" || req.status === statusFilter;
      const matchesSearch =
        req.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
        req.user.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    });
  }, [requests, searchQuery, statusFilter]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-oswald font-medium tracking-tight">
          Requêtes API
        </h1>
        <p className="text-muted-foreground">
          Historique et gestion des requêtes du système RAG
        </p>
      </div>

      {requestsQuery.isError && (
        <QueryError error={requestsQuery.error} onRetry={() => void requestsQuery.refetch()} />
      )}

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Rechercher par question ou utilisateur..."
                className="pl-10"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Statut" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous</SelectItem>
                <SelectItem value="success">Succès</SelectItem>
                <SelectItem value="error">Échec</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline">
              <Download className="w-4 h-4 mr-2" />
              Exporter
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Requests Table */}
      <Card>
        <CardHeader>
          <CardTitle>Liste des requêtes</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left p-4 text-xs font-space uppercase tracking-widest text-muted-foreground">
                    ID
                  </th>
                  <th className="text-left p-4 text-xs font-space uppercase tracking-widest text-muted-foreground">
                    Timestamp
                  </th>
                  <th className="text-left p-4 text-xs font-space uppercase tracking-widest text-muted-foreground">
                    Utilisateur
                  </th>
                  <th className="text-left p-4 text-xs font-space uppercase tracking-widest text-muted-foreground">
                    Question
                  </th>
                  <th className="text-left p-4 text-xs font-space uppercase tracking-widest text-muted-foreground">
                    Statut
                  </th>
                  <th className="text-left p-4 text-xs font-space uppercase tracking-widest text-muted-foreground">
                    Latence
                  </th>
                  <th className="text-left p-4 text-xs font-space uppercase tracking-widest text-muted-foreground">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredRequests.map((request) => (
                  <tr
                    key={request.id}
                    className="border-b border-border hover:bg-muted/30 transition-colors"
                  >
                    <td className="p-4 font-mono text-sm">{request.id}</td>
                    <td className="p-4 text-sm text-muted-foreground">
                      {request.timestamp}
                    </td>
                    <td className="p-4 text-sm">{request.user}</td>
                    <td className="p-4 text-sm max-w-[300px] truncate">
                      {request.question}
                    </td>
                    <td className="p-4">
                      <Badge
                        className={cn(
                          request.status === "success"
                            ? "bg-success hover:bg-success/90"
                            : "bg-destructive"
                        )}
                      >
                        {request.status === "success" ? "Succès" : "Échec"}
                      </Badge>
                    </td>
                    <td className="p-4 font-mono text-sm">
                      {request.latency.toFixed(2)}s
                    </td>
                    <td className="p-4">
                      <Button variant="ghost" size="sm">
                        <Eye className="w-4 h-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {/* Pagination */}
          <div className="flex items-center justify-between p-4 border-t border-border">
            <p className="text-sm text-muted-foreground">
              Affichage de 1 à {filteredRequests.length} sur {requests.length} résultats
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled>
                Précédent
              </Button>
              <Button variant="outline" size="sm" disabled>
                Suivant
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminApiRequests;
