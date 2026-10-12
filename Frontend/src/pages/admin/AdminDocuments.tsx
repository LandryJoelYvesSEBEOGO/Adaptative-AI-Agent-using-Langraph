import { FileText, Loader2, RefreshCw, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { errorMessage } from "@/api/errors";
import { useDeleteDocument, useDocuments, useReindexDocument, useUploadDocument } from "@/api/hooks";
import type { DocumentInfo } from "@/api/types";
import ConfirmDialog from "@/components/ConfirmDialog";
import MetricCard from "@/components/admin/MetricCard";
import QueryError from "@/components/QueryError";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const STATUS: Record<DocumentInfo["status"], { label: string; className: string }> = {
  pending: { label: "En attente", className: "bg-muted text-muted-foreground" },
  processing: { label: "Indexation…", className: "bg-warning/20 text-warning-foreground" },
  ready: { label: "Prêt", className: "bg-success/15 text-success" },
  failed: { label: "Échec", className: "bg-destructive/15 text-destructive" },
};

const AdminDocuments = () => {
  const documents = useDocuments();
  const upload = useUploadDocument();
  const reindex = useReindexDocument();
  const remove = useDeleteDocument();
  const { toast } = useToast();
  const fileInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [toDelete, setToDelete] = useState<DocumentInfo | null>(null);

  const rows = documents.data ?? [];
  const ready = rows.filter((d) => d.status === "ready");
  const failed = rows.filter((d) => d.status === "failed").length;
  const inProgress = rows.filter((d) => d.status === "pending" || d.status === "processing").length;
  const chunks = ready.reduce((sum, d) => sum + (d.chunk_count ?? 0), 0);

  const uploadFiles = async (files: FileList | File[]) => {
    for (const file of Array.from(files)) {
      try {
        await upload.mutateAsync({ file });
        toast({ title: "Téléversé", description: `${file.name} : indexation en cours.` });
      } catch (error) {
        toast({ title: `Échec : ${file.name}`, description: errorMessage(error), variant: "destructive" });
      }
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-oswald font-medium tracking-tight">Documents</h1>
        <p className="text-muted-foreground">
          Corpus interrogé par l'assistant. Nommer les fichiers <code>SOCIETE_ANNEE_10K.pdf</code> renseigne
          automatiquement la société, l'exercice et le type.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard title="Documents" value={rows.length} icon={FileText} />
        <MetricCard title="Prêts" value={ready.length} subtitle={`${chunks} passages indexés`} icon={FileText} variant="success" />
        <MetricCard title="En cours" value={inProgress} icon={Loader2} variant="warning" />
        <MetricCard title="En échec" value={failed} icon={FileText} variant={failed ? "destructive" : "default"} />
      </div>

      <Card
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          void uploadFiles(event.dataTransfer.files);
        }}
        className={cn("border-dashed transition-colors", dragging && "border-primary bg-primary/5")}
      >
        <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
          <Upload className="w-8 h-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Glissez des PDF ici ou</p>
          <Button onClick={() => fileInput.current?.click()} disabled={upload.isPending}>
            {upload.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Choisir des fichiers
          </Button>
          <input
            ref={fileInput}
            type="file"
            accept="application/pdf,.pdf"
            multiple
            hidden
            aria-label="Fichiers PDF"
            onChange={(event) => {
              if (event.target.files) void uploadFiles(event.target.files);
              event.target.value = "";
            }}
          />
        </CardContent>
      </Card>

      {documents.isError && <QueryError error={documents.error} onRetry={() => void documents.refetch()} />}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-oswald font-medium">Corpus</CardTitle>
        </CardHeader>
        <CardContent>
          {documents.isLoading ? (
            <p className="text-sm text-muted-foreground">Chargement…</p>
          ) : rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucun document. Téléversez un premier PDF.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fichier</TableHead>
                  <TableHead>Société</TableHead>
                  <TableHead>Exercice</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead className="text-right">Pages</TableHead>
                  <TableHead className="text-right">Passages</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="font-medium">{doc.filename}</TableCell>
                    <TableCell>{doc.company ?? "—"}</TableCell>
                    <TableCell>{doc.fiscal_year ?? "—"}</TableCell>
                    <TableCell>{doc.doc_type ?? "—"}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={cn("border-0", STATUS[doc.status].className)} title={doc.error ?? undefined}>
                        {STATUS[doc.status].label}
                      </Badge>
                      {doc.status === "failed" && doc.error && (
                        <p className="mt-1 max-w-xs truncate text-xs text-destructive" title={doc.error}>
                          {doc.error}
                        </p>
                      )}
                    </TableCell>
                    <TableCell className="text-right">{doc.pages ?? "—"}</TableCell>
                    <TableCell className="text-right">{doc.chunk_count ?? "—"}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Réindexer ${doc.filename}`}
                        disabled={doc.status === "processing" || reindex.isPending}
                        onClick={() =>
                          reindex.mutate(doc.id, {
                            onError: (error) =>
                              toast({ title: "Réindexation impossible", description: errorMessage(error), variant: "destructive" }),
                          })
                        }
                      >
                        <RefreshCw className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Supprimer ${doc.filename}`}
                        className="text-muted-foreground hover:text-destructive"
                        onClick={() => setToDelete(doc)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={toDelete !== null}
        title="Supprimer ce document ?"
        description={`« ${toDelete?.filename ?? ""} » et ses passages indexés seront supprimés. Les conversations existantes conservent leurs citations.`}
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

export default AdminDocuments;
