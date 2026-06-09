import React from 'react';

export default function FeatureShowcase() {
  const features = [
    {
      title: "Smart AI Itineraries",
      description: "Automated, personalized city exploration plans generated the moment your accommodation is locked.",
      image: "/itinerary.jpg", 
      colSpan: "md:col-span-2", 
      gradient: "from-blue-500/10 to-transparent",
      containerHeight: "h-72 md:h-80", 
      imgClass: "object-cover object-[center_35%] scale-[1.05]", 
    },
    {
      title: "The Secure Vault",
      description: "All your active deployments, live PNRs, and waitlist probabilities locked in one clean dashboard.",
      image: "/vault.png", 
      colSpan: "md:col-span-1", 
      gradient: "from-emerald-500/10 to-transparent",
      containerHeight: "h-64 md:h-72",
      // 👇 Isko left-top par focus kiya taaki Train ka naam aur PNR card theek se dikhe
      imgClass: "object-cover object-left-top", 
    },
    {
      title: "Project Shakti Shield",
      description: "Military-grade background tracking for solo travelers. Auto-dispatches RPF & Zero-FIRs on SOS.",
      image: "/shakti-alert.png", 
      colSpan: "md:col-span-1",
      gradient: "from-rose-500/10 to-transparent",
      containerHeight: "h-64 md:h-80",
      // 👇 Isko 'contain' kiya aur thoda narrow banaya taaki Mobile chat jaisa lage aur text side se na kate
      imgClass: "w-[90%] mx-auto object-contain object-top", 
    },
    {
      title: "End-to-End Orchestration",
      description: "From wake-up calls to PDF invoices and cab coordination, Agentra handles the logistics directly on Telegram.",
      image: "/invoice.png", 
      colSpan: "md:col-span-2",
      gradient: "from-indigo-500/10 to-transparent",
      containerHeight: "h-64 md:h-80",
      imgClass: "object-cover object-center",
    }
  ];

  return (
    <section className="py-32 bg-[#0B1120] relative overflow-hidden">
      {/* Background Subtle Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-blue-500/5 blur-[150px] rounded-full pointer-events-none"></div>

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        <div className="text-center mb-20">
          <h2 className="text-4xl md:text-5xl font-extrabold text-white mb-6 tracking-tight">
            See <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">Agentra in Action</span>
          </h2>
          <p className="text-xl text-slate-400 font-light max-w-2xl mx-auto">
            Real-time orchestration, live previews, and automated safeguards. Everything running seamlessly in the background.
          </p>
        </div>

        {/* BENTO GRID LAYOUT - Gap badha diya (gap-6 se gap-8/10) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-10">
          {features.map((feature, idx) => (
             <div 
             key={idx} 
             className={`group relative rounded-3xl overflow-hidden border border-slate-800/80 bg-[#0F172A]/80 backdrop-blur-md transition-all duration-500 hover:border-slate-600 hover:shadow-2xl hover:shadow-blue-500/5 flex flex-col ${feature.colSpan}`}
           >
             {/* Text Content - Padding badha di (p-10) */}
             <div className="relative z-20 p-8 lg:p-10 pb-0">
               <h3 className="text-2xl font-bold text-white mb-3 tracking-wide">{feature.title}</h3>
               <p className="text-slate-400 text-sm leading-relaxed max-w-md">
                 {feature.description}
               </p>
             </div>

             {/* Image Container - Dynamic Heights & Spacing */}
             <div className={`relative mt-8 px-8 ${feature.containerHeight} overflow-hidden rounded-b-3xl flex justify-center items-start mt-auto`}>
               {/* Fade gradient so harsh lines hide */}
               <div className={`absolute inset-0 bg-gradient-to-b ${feature.gradient} z-10 pointer-events-none`}></div>
               
               <img 
                 src={feature.image} 
                 alt={feature.title} 
                 className={`w-full h-full rounded-t-xl border border-slate-700/50 shadow-2xl transition-transform duration-700 group-hover:-translate-y-3 group-hover:scale-[1.03] relative z-0 ${feature.imgClass}`}
               />
             </div>
           </div>
          ))}
        </div>
      </div>
    </section>
  );
}