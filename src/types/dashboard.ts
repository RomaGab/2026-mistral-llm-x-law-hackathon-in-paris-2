export type FactValue = boolean | null;

export type FactorDefinition = {
  id: string;
  libelle: string;
  question: string;
  groupe: string;
  importance: number;
};

export type FactorAnalysis = {
  est_pivot: boolean;
  niveau: string;
  type: string;
  probabilite_si_vrai: number;
  probabilite_si_faux: number;
  contribution: number;
  ecartees_si_vrai: string[];
  ecartees_si_faux: string[];
};

export type DecisionAnalysis = {
  id: string;
  retenue: boolean;
  motif_exclusion: string | null;
  proximite: number;
  poids: number;
  alignement: Record<string, string>;
  s_applique_a_fortiori?: boolean;
  arguments_manquants?: { facteur: string; valeur: boolean }[];
  arguments_contraires?: { facteur: string; valeur: boolean }[];
};

export type AnalysisResult = {
  prediction: { probabilite: number; intervalle: number[]; issue: boolean; incertain: boolean };
  majeure: { issue: boolean; probabilite: number; decisions: string[] };
  exception: {
    issue: boolean;
    probabilite: number;
    conditions: { facteur: string; valeur: boolean; probabilite_si: number }[];
    decision_reference: string | null;
  } | null;
  pivots: string[];
  pivots_combines: { facteurs: string[]; valeurs: boolean[]; probabilite_si: number }[];
  facteurs: Record<string, FactorAnalysis>;
  decisions: DecisionAnalysis[];
  avertissements: string[];
};

export type CaseDecision = {
  id: string;
  intitule: string;
  juridiction: string;
  date: string;
  issue: boolean;
  url: string | null;
};

export type DashboardDossier = {
  grille: {
    facteurs: FactorDefinition[];
    issue: { si_vrai: string; si_faux: string };
  };
  cas: {
    id: string;
    question: string;
    facteurs: Record<string, FactValue>;
    preuves: Record<string, { extrait: string | null; confiance: number; source: string }>;
  };
  decisions: CaseDecision[];
  parametres: { niveau_intervalle: number };
  resultat: AnalysisResult;
};

export type FactOverride = { factorId: string; value: FactValue };
