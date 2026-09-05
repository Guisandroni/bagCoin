import { redirect } from "next/navigation";

// import { LandingNavbar } from "@/components/landing/navbar";
// import { HeroSection } from "@/components/landing/hero";
// import { FeaturesGrid } from "@/components/landing/features";
// import { QuoteSection } from "@/components/landing/quote";
// import { CTASection } from "@/components/landing/cta";
// import { LandingFooter } from "@/components/landing/footer";

export default function HomePage() {
  redirect("/login");

  // return (
  //   <div className="min-h-screen bg-[#fafafa] selection:bg-brand selection:text-white">
  //     <LandingNavbar />
  //     <HeroSection />
  //     <main className="mx-auto max-w-7xl px-4 py-24">
  //       <FeaturesGrid />
  //       <QuoteSection />
  //       <CTASection />
  //     </main>
  //     <LandingFooter />
  //   </div>
  // );
}
