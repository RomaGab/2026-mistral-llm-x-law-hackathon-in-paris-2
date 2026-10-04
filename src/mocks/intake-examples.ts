import type { CaseIntakeDraft } from "@/types/case-intake";

type IntakeExample = Pick<CaseIntakeDraft, "question" | "description" | "ressort"> & {
  id: string;
  label: string;
};

export const intakeExamples: IntakeExample[] = [
  {
    id: "chauffeur",
    label: "Ride-hailing driver",
    question:
      "Can a ride-hailing driver have their relationship with a platform reclassified as employment?",
    description:
      "The platform tracks their trips in real time and sets fares. They can work for competitors. Whether the platform uses account deactivation as a penalty remains to be confirmed.",
    ressort: null,
  },
  {
    id: "livreur",
    label: "Platform delivery rider",
    question:
      "Is a bicycle delivery rider an employee or an independent contractor of their platform?",
    description:
      "The rider chooses their hours and uses their own bicycle. The platform assigns deliveries and sets their pay. The consequences of refusing a delivery remain to be verified.",
    ressort: null,
  },
];
