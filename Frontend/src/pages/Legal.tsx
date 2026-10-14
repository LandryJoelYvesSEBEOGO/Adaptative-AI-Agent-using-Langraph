import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

// Les champs « [À COMPLÉTER : …] » sont à renseigner par l'éditeur avant toute mise en production.
// Ce texte est un modèle de départ, pas un avis juridique : à faire valider.
const Todo = ({ children }: { children: ReactNode }) => (
  <mark className="rounded bg-warning/20 px-1 text-foreground">[À COMPLÉTER : {children}]</mark>
);

const Shell = ({ title, children }: { title: string; children: ReactNode }) => (
  <div className="min-h-screen bg-background">
    <main className="mx-auto max-w-3xl px-4 py-12">
      <Link
        to="/"
        className="mb-8 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Retour
      </Link>
      <h1 className="mb-8 text-4xl font-oswald font-medium tracking-tight">{title}</h1>
      <div className="space-y-8 text-sm leading-relaxed [&_h2]:mb-2 [&_h2]:text-lg [&_h2]:font-semibold [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-6">
        {children}
      </div>
    </main>
  </div>
);

export const LegalNotice = () => (
  <Shell title="Mentions légales">
    <section>
      <h2>Éditeur du service</h2>
      <p>
        <Todo>nom ou raison sociale</Todo>, <Todo>forme juridique et capital</Todo>,{" "}
        <Todo>adresse du siège</Todo>, <Todo>SIREN / numéro d'immatriculation</Todo>.
      </p>
      <p>
        Directeur de la publication : <Todo>nom</Todo>. Contact : <Todo>adresse e-mail</Todo>.
      </p>
    </section>
    <section>
      <h2>Hébergement</h2>
      <p>
        <Todo>nom, adresse et contact de l'hébergeur</Todo>.
      </p>
    </section>
    <section>
      <h2>Nature du service</h2>
      <p>
        RAG System répond à des questions à partir de documents indexés, à l'aide d'un modèle de langage. Les
        réponses sont générées automatiquement et peuvent comporter des erreurs : elles ne constituent pas un conseil
        (financier, juridique ou autre) et doivent être vérifiées dans les sources citées.
      </p>
    </section>
    <section>
      <h2>Propriété intellectuelle</h2>
      <p>
        Les documents indexés restent la propriété de leurs titulaires. Le code et les éléments graphiques du service
        sont protégés ; toute reproduction non autorisée est interdite. <Todo>licence applicable</Todo>
      </p>
    </section>
  </Shell>
);

export const PrivacyPolicy = () => (
  <Shell title="Politique de confidentialité">
    <section>
      <h2>Responsable du traitement</h2>
      <p>
        <Todo>identité et contact de l'éditeur</Todo>. Délégué à la protection des données :{" "}
        <Todo>contact, ou « sans objet »</Todo>.
      </p>
    </section>
    <section>
      <h2>Données collectées et finalités</h2>
      <ul>
        <li>
          <strong>Compte</strong> : nom, adresse e-mail, mot de passe (conservé uniquement haché). Finalité :
          authentifier l'utilisateur.
        </li>
        <li>
          <strong>Conversations</strong> : vos questions, les réponses générées, leurs sources et vos avis (pouce
          haut / bas). Finalité : fournir le service et retrouver votre historique.
        </li>
        <li>
          <strong>Données techniques</strong> : date, durée et statut de chaque requête, identifiant de requête dans
          les journaux. Finalité : sécurité, mesure de qualité et supervision du service.
        </li>
      </ul>
      <p>
        Base légale : exécution du service demandé (contrat) et intérêt légitime de sécurité.{" "}
        <Todo>vérifier avec votre conseil</Todo>
      </p>
    </section>
    <section>
      <h2>Destinataires et sous-traitants</h2>
      <p>
        Pour répondre, le texte de vos questions et des extraits de documents sont transmis à des prestataires
        d'IA : fournisseur du modèle de langage, des embeddings et du reranking, et, lorsque les documents ne
        suffisent pas, service de recherche web (Tavily). <Todo>liste exacte des prestataires activés, pays de
        traitement et garanties de transfert</Todo>. <strong>N'indiquez pas de données personnelles sensibles dans
        vos questions.</strong>
      </p>
    </section>
    <section>
      <h2>Cookies</h2>
      <p>
        Le service dépose uniquement des cookies strictement nécessaires à la connexion (jetons de session, httpOnly,
        non lisibles par les scripts). Aucun cookie publicitaire ni de mesure d'audience : aucun bandeau de
        consentement n'est donc requis. Le choix du thème clair/sombre est mémorisé localement dans votre navigateur.
      </p>
    </section>
    <section>
      <h2>Durée de conservation</h2>
      <p>
        Les données du compte et les conversations sont conservées tant que le compte existe ; les sauvegardes
        techniques sont conservées <Todo>durée, 14 jours par défaut</Todo>. <Todo>durée de conservation des
        journaux et des métriques</Todo>
      </p>
    </section>
    <section>
      <h2>Vos droits</h2>
      <p>
        Vous pouvez demander l'accès, la rectification, l'effacement, la limitation ou la portabilité de vos données,
        et vous opposer à leur traitement, en écrivant à <Todo>adresse e-mail</Todo>. Vous pouvez aussi saisir la
        CNIL (cnil.fr). La suppression d'un compte efface ses conversations.
      </p>
    </section>
  </Shell>
);
