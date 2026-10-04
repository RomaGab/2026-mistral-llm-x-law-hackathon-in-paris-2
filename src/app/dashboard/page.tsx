import type { Metadata } from "next";
import { DashboardWorkspace } from "@/components/dashboard/dashboard-workspace";

export const metadata: Metadata = { title: "pivot — Case analysis" };

export default function DashboardPage() {
  return <DashboardWorkspace />;
}
