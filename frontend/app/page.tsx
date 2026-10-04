import Link from "next/link";
import {
  ArrowRight,
  Bot,
  Brain,
  FileText,
  Network,
  Quote,
  Sparkles,
  Zap,
  Shield,
  GitBranch,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const features = [
  {
    icon: Quote,
    title: "Grounded Citations",
    desc: "Every sentence is backed by a source span. Click to jump to the exact page. Zero hallucinated references.",
  },
  {
    icon: Network,
    title: "Knowledge Graphs",
    desc: "Entities, relationships, and timelines auto-extracted into an interactive graph you can explore.",
  },
  {
    icon: Bot,
    title: "Multi-Agent Research",
    desc: "Specialized agents — Research, Citation, Writing, Fact-Check — orchestrated by LangGraph.",
  },
  {
    icon: Brain,
    title: "Long-Term Memory",
    desc: "Working, episodic, semantic, procedural memory with consolidation and importance decay.",
  },
  {
    icon: Shield,
    title: "Enterprise-Ready",
    desc: "Multi-tenant, RBAC, MFA, audit logs, SSO. SOC2-aligned by design.",
  },
  {
    icon: Zap,
    title: "Local-First AI",
    desc: "Runs on Ollama (qwen2.5:3b). Swap to OpenAI, Claude, Gemini, or vLLM with one env var.",
  },
];

const tiers = [
  {
    name: "Free",
    price: "$0",
    features: ["3 notebooks", "100 documents", "Local AI (Ollama)", "Community support"],
    cta: "Get started",
    href: "/register",
  },
  {
    name: "Pro",
    price: "$24",
    popular: true,
    features: ["Unlimited notebooks", "10k documents", "Cloud LLMs", "Knowledge graphs", "Priority support"],
    cta: "Start Pro trial",
    href: "/register?plan=pro",
  },
  {
    name: "Team",
    price: "$79",
    features: ["Everything in Pro", "10 seats", "Collaboration", "Audit logs", "SSO"],
    cta: "Contact sales",
    href: "/register?plan=team",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
        <div className="container flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 text-white">
              <Brain className="h-4 w-4" />
            </div>
            <span className="font-semibold tracking-tight">CortexFlow</span>
          </Link>
          <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
            <Link href="#features" className="hover:text-foreground">Features</Link>
            <Link href="#demo" className="hover:text-foreground">Demo</Link>
            <Link href="#pricing" className="hover:text-foreground">Pricing</Link>
            <Link href="/docs" className="hover:text-foreground">Docs</Link>
          </nav>
          <div className="flex items-center gap-2">
            <Button variant="ghost" asChild>
              <Link href="/login">Sign in</Link>
            </Button>
            <Button asChild>
              <Link href="/register">Get started <ArrowRight className="h-4 w-4" /></Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-brand-500/10 via-background to-background" />
        <div className="container relative py-24 text-center">
          <Badge variant="default" className="mb-4 gap-1">
            <Sparkles className="h-3 w-3" /> Open-source · Self-hostable · Production-grade
          </Badge>
          <h1 className="mx-auto max-w-4xl text-balance text-4xl font-bold tracking-tight sm:text-6xl">
            Your <span className="bg-gradient-to-r from-brand-400 to-brand-600 bg-clip-text text-transparent">AI research</span> workspace,
            grounded by evidence.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-balance text-lg text-muted-foreground">
            Upload your documents, chat with them through specialized agents, and get every claim
            backed by a clickable citation. Built to surpass NotebookLM in extensibility, reasoning,
            and memory.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Button size="lg" asChild>
              <Link href="/register">Start free <ArrowRight className="h-4 w-4" /></Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/dashboard">Live demo</Link>
            </Button>
          </div>
          <div className="mt-4 text-xs text-muted-foreground">
            Local-first with <code className="rounded bg-muted px-1.5 py-0.5">ollama · qwen2.5:3b</code> · No credit card required
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="container py-20">
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold tracking-tight">Everything NotebookLM has, and more.</h2>
          <p className="mt-3 text-muted-foreground">A modular platform engineered for serious research workflows.</p>
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="group rounded-xl border bg-card p-6 transition hover:border-primary/40 hover:shadow-md"
            >
              <div className="mb-4 grid h-10 w-10 place-items-center rounded-lg bg-primary/10 text-primary">
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="font-semibold">{f.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Demo strip */}
      <section id="demo" className="border-y bg-muted/30">
        <div className="container py-20 text-center">
          <Badge variant="secondary" className="mb-4"><GitBranch className="mr-1 h-3 w-3" /> Pipeline</Badge>
          <h2 className="text-3xl font-bold tracking-tight">Retrieve → Rerank → Reason → Ground → Answer</h2>
          <div className="mx-auto mt-10 flex max-w-4xl flex-wrap items-center justify-center gap-3 text-sm">
            {["Upload", "Parse + OCR", "Chunk", "Embed", "Vector Search", "RAG Agent", "Citations"].map((step, i) => (
              <div key={step} className="flex items-center gap-3">
                <span className="rounded-full border bg-card px-4 py-2 font-medium shadow-sm">{step}</span>
                {i < 6 && <ArrowRight className="h-4 w-4 text-muted-foreground" />}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="container py-20">
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold tracking-tight">Simple, usage-based pricing</h2>
          <p className="mt-3 text-muted-foreground">Start free. Upgrade when you need more.</p>
        </div>
        <div className="grid gap-6 md:grid-cols-3">
          {tiers.map((tier) => (
            <div
              key={tier.name}
              className={`relative rounded-xl border bg-card p-6 ${
                tier.popular ? "border-primary shadow-lg ring-1 ring-primary" : ""
              }`}
            >
              {tier.popular && (
                <Badge className="absolute -top-3 left-1/2 -translate-x-1/2">Most popular</Badge>
              )}
              <h3 className="font-semibold">{tier.name}</h3>
              <div className="mt-2 flex items-baseline gap-1">
                <span className="text-3xl font-bold">{tier.price}</span>
                <span className="text-sm text-muted-foreground">/mo</span>
              </div>
              <ul className="mt-6 space-y-2 text-sm text-muted-foreground">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary" /> {f}
                  </li>
                ))}
              </ul>
              <Button className="mt-6 w-full" variant={tier.popular ? "default" : "outline"} asChild>
                <Link href={tier.href}>{tier.cta}</Link>
              </Button>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t">
        <div className="container flex flex-col items-center justify-between gap-4 py-8 text-sm text-muted-foreground sm:flex-row">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4" /> © 2026 CortexFlow · MIT License
          </div>
          <div className="flex gap-6">
            <Link href="/docs">Docs</Link>
            <Link href="/api-playground">API</Link>
            <Link href="https://github.com" target="_blank">GitHub</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
