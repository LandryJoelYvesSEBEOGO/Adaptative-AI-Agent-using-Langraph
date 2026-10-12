import { useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";

// Le worker pdf.js est servi par Vite (pas de CDN externe)
pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/legacy/build/pdf.worker.min.mjs", import.meta.url).toString();

// Constante hors du composant : react-pdf recharge le document si `options` change d'identité
const DOCUMENT_OPTIONS = { withCredentials: true } as const;

interface PdfPreviewProps {
  url: string;
  page: number;
  width: number;
}

/** Aperçu d'une page de PDF. Le cookie de session accompagne la requête. */
const PdfPreview = ({ url, page, width }: PdfPreviewProps) => {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return <p className="text-sm text-muted-foreground">Aperçu indisponible pour ce document.</p>;
  }
  return (
    <Document
      file={url}
      options={DOCUMENT_OPTIONS}
      loading={<p className="text-sm text-muted-foreground">Chargement du document…</p>}
      onLoadError={() => setFailed(true)}
      onSourceError={() => setFailed(true)}
    >
      <Page
        pageNumber={page}
        width={width}
        renderAnnotationLayer={false}
        renderTextLayer={false}
        onLoadError={() => setFailed(true)}
        loading={<p className="text-sm text-muted-foreground">Chargement de la page…</p>}
      />
    </Document>
  );
};

export default PdfPreview;
