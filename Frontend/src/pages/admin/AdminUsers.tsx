import { Shield, Users } from "lucide-react";
import { useState } from "react";

import { errorMessage } from "@/api/errors";
import { useDeleteUser, useUpdateUserRole, useUsers } from "@/api/hooks";
import type { AdminUser, UserRole } from "@/api/types";
import { useSession } from "@/auth/session";
import ConfirmDialog from "@/components/ConfirmDialog";
import MetricCard from "@/components/admin/MetricCard";
import QueryError from "@/components/QueryError";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";

const dateFormat = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });
const formatDate = (value: string | null | undefined) => (value ? dateFormat.format(new Date(value)) : "—");

const AdminUsers = () => {
  const users = useUsers();
  const updateRole = useUpdateUserRole();
  const remove = useDeleteUser();
  const { data: me } = useSession();
  const { toast } = useToast();
  const [toDelete, setToDelete] = useState<AdminUser | null>(null);

  const rows = users.data ?? [];
  const admins = rows.filter((u) => u.role === "admin").length;
  const requests = rows.reduce((sum, u) => sum + u.requests, 0);

  const changeRole = (user: AdminUser, role: UserRole) =>
    updateRole.mutate(
      { id: user.id, role },
      {
        onSuccess: () => toast({ title: "Rôle modifié", description: `${user.email} : ${role}` }),
        onError: (error) =>
          toast({ title: "Modification impossible", description: errorMessage(error), variant: "destructive" }),
      },
    );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-oswald font-medium tracking-tight">Utilisateurs</h1>
        <p className="text-muted-foreground">Comptes, rôles et activité</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="Utilisateurs" value={rows.length} icon={Users} />
        <MetricCard title="Administrateurs" value={admins} icon={Shield} />
        <MetricCard title="Requêtes RAG" value={requests} icon={Users} />
      </div>

      {users.isError && <QueryError error={users.error} onRetry={() => void users.refetch()} />}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-oswald font-medium">Comptes</CardTitle>
        </CardHeader>
        <CardContent>
          {users.isLoading ? (
            <p className="text-sm text-muted-foreground">Chargement…</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Utilisateur</TableHead>
                  <TableHead>Rôle</TableHead>
                  <TableHead>Inscrit le</TableHead>
                  <TableHead className="text-right">Conversations</TableHead>
                  <TableHead className="text-right">Requêtes</TableHead>
                  <TableHead>Dernière activité</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((user) => {
                  const isSelf = user.id === me?.id;
                  return (
                    <TableRow key={user.id}>
                      <TableCell>
                        <p className="font-medium">
                          {user.name}
                          {isSelf && <span className="ml-2 text-xs text-muted-foreground">(vous)</span>}
                        </p>
                        <p className="text-xs text-muted-foreground">{user.email}</p>
                      </TableCell>
                      <TableCell>
                        <Select
                          value={user.role}
                          disabled={isSelf || updateRole.isPending}
                          onValueChange={(role) => changeRole(user, role as UserRole)}
                        >
                          <SelectTrigger className="w-36" aria-label={`Rôle de ${user.email}`}>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="user">Utilisateur</SelectItem>
                            <SelectItem value="admin">Administrateur</SelectItem>
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>{formatDate(user.created_at)}</TableCell>
                      <TableCell className="text-right">{user.conversations}</TableCell>
                      <TableCell className="text-right">{user.requests}</TableCell>
                      <TableCell>{formatDate(user.last_activity)}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={isSelf}
                          className="text-muted-foreground hover:text-destructive"
                          onClick={() => setToDelete(user)}
                        >
                          Supprimer
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={toDelete !== null}
        title="Supprimer ce compte ?"
        description={`${toDelete?.email ?? ""} et toutes ses conversations seront supprimés définitivement. L'historique des requêtes (métriques) est conservé de façon anonyme.`}
        onCancel={() => setToDelete(null)}
        onConfirm={() => {
          if (!toDelete) return;
          remove.mutate(toDelete.id, {
            onError: (error) =>
              toast({ title: "Suppression impossible", description: errorMessage(error), variant: "destructive" }),
          });
          setToDelete(null);
        }}
      />
    </div>
  );
};

export default AdminUsers;
