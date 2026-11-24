import { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import { MotionConfig } from "motion/react";
import type { Summary } from "./lib/api";
import { useApi } from "./lib/hooks";
import { Footer, Nav, Page } from "./components/ui/Shell";
import { Empty } from "./components/ui/States";
import { Home } from "./pages/Home";
import { Trial, TrialIndex } from "./pages/Trial";
import { Generation } from "./pages/Generation";
import { Instincts } from "./pages/Instincts";
import { Evidence } from "./pages/Evidence";

function ScrollTop() {
  const { pathname } = useLocation();
  useEffect(() => window.scrollTo(0, 0), [pathname]);
  return null;
}

export default function App() {
  const { data: summary } = useApi<Summary>("/api/summary", 15000);
  const mode = summary?.mode;
  return (
    <MotionConfig reducedMotion="user">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-lg focus:bg-moon focus:px-4 focus:py-2 focus:text-night">
        Skip to content
      </a>
      <ScrollTop />
      <Nav summary={summary} />
      <Routes>
        <Route path="/" element={<Home summary={summary} />} />
        <Route path="/trial" element={<TrialIndex summary={summary} />} />
        <Route path="/trial/:gen" element={<Trial mode={mode} />} />
        <Route path="/gen/:gen" element={<Generation mode={mode} />} />
        <Route path="/instincts" element={<Instincts mode={mode} />} />
        <Route path="/evidence" element={<Evidence summary={summary} />} />
        <Route
          path="*"
          element={
            <Page>
              <Empty title="Not in the register" action={{ to: "/", label: "Go to the family" }}>
                There's no generation, trial or page at this address.
              </Empty>
            </Page>
          }
        />
      </Routes>
      <Footer />
    </MotionConfig>
  );
}
