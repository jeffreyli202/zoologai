import { Sidebar } from "@/components/layout/Sidebar";

type AppShellProps = {
  children: React.ReactNode;
};

/** Shared page chrome: sidebar + main content area. */
export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <Sidebar />
      <main className="flex-1 px-4 py-6 md:px-8 md:py-10 lg:px-12">
        <div className="mx-auto w-full max-w-5xl">{children}</div>
      </main>
    </div>
  );
}
