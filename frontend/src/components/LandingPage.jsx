import React from 'react';
import { Sparkles, MapPin, ShieldCheck, ArrowRight, Train, Plane, MessageSquare, CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react';
import FeatureShowcase from './FeatureShowcase';

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-[#0B1120] text-slate-300 font-sans selection:bg-emerald-500/30 selection:text-emerald-200 overflow-hidden">
      
      {/* --- NAVBAR --- */}
      <nav className="fixed w-full z-50 bg-[#0B1120]/80 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 h-20 flex justify-between items-center">
          {/* Logo Wrapped in a White Pill for JPEG compatibility */}
          <div className="flex items-center space-x-3 cursor-pointer">
            <div className="bg-white p-1.5 rounded-xl shadow-[0_0_15px_rgba(59,130,246,0.2)]">
              <img src="logo2.png" alt="Agentra Logo" className="h-9 w-auto mix-blend-multiply" />
            </div>
            <span className="text-xl font-bold text-white tracking-wide">Agentra</span>
          </div>
          
          <div className="hidden md:flex space-x-8">
            <a href="#how-it-works" className="text-slate-400 hover:text-white font-medium transition-colors">How it works</a>
            <a href="#features" className="text-slate-400 hover:text-white font-medium transition-colors">Features</a>
            <a href="#integrations" className="text-slate-400 hover:text-white font-medium transition-colors">Integrations</a>
          </div>

          <div className="flex items-center space-x-4">
            <SignedOut>
              <SignInButton mode="modal">
                <button className="hidden sm:block text-slate-400 font-medium hover:text-white transition-colors">
                  Log in
                </button>
              </SignInButton>
              <SignInButton mode="modal">
                <button className="bg-white/10 border border-white/20 text-white px-6 py-2.5 rounded-full font-medium hover:bg-white/20 transition-all backdrop-blur-md">
                  Get Started
                </button>
              </SignInButton>
            </SignedOut>
            
            <SignedIn>
              <Link to="/dashboard" className="text-sm font-bold bg-gradient-to-r from-blue-600 to-emerald-500 px-5 py-2 rounded-lg text-white hover:shadow-[0_0_15px_rgba(16,185,129,0.4)] transition-all">
                Access Terminal
              </Link>
              <UserButton afterSignOutUrl="/" /> 
            </SignedIn>
          </div>
        </div>
      </nav>

      {/* --- HERO SECTION --- */}
      <div className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden">
        {/* Deep Dark Background Glowing Orbs */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-gradient-to-r from-blue-600/20 to-emerald-500/20 blur-[120px] -z-10 rounded-full"></div>
        
        <div className="max-w-7xl mx-auto px-6 relative z-10 text-center">
          
          {/* Floating UI Card 1 (Left) */}
          <div className="hidden lg:flex absolute top-10 left-10 bg-slate-900/80 backdrop-blur-md p-4 rounded-2xl shadow-2xl border border-slate-700/50 items-center space-x-3 animate-[bounce_6s_infinite]">
            <div className="bg-blue-500/20 p-2 rounded-full"><Sparkles className="h-5 w-5 text-blue-400" /></div>
            <div className="text-left">
              <p className="text-sm font-bold text-slate-200">Alternative Route Found</p>
              <p className="text-xs text-slate-400">Cab to Jhansi + Vande Bharat</p>
            </div>
          </div>

          {/* Floating UI Card 2 (Right) */}
          <div className="hidden lg:flex absolute top-40 right-10 bg-slate-900/80 backdrop-blur-md p-4 rounded-2xl shadow-2xl border border-slate-700/50 items-center space-x-3 animate-[bounce_7s_infinite_reverse]">
            <div className="bg-emerald-500/20 p-2 rounded-full"><CheckCircle2 className="h-5 w-5 text-emerald-400" /></div>
            <div className="text-left">
              <p className="text-sm font-bold text-slate-200">WL Prediction: 84%</p>
              <p className="text-xs text-slate-400">Likely to confirm before chart</p>
            </div>
          </div>

          <div className="inline-flex items-center px-4 py-2 rounded-full bg-slate-800/50 border border-slate-700 shadow-sm text-sm font-medium text-slate-300 mb-8 backdrop-blur-sm">
            <Sparkles className="w-4 h-4 text-emerald-400 mr-2" />
            Next-Gen Autonomous Travel Agent
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold text-white tracking-tight mb-8 leading-[1.1]">
            Travel planning,<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">
              beautifully orchestrated.
            </span>
          </h1>
          
          <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed font-light">
            Stop stressing over waitlists and broken routes. Agentra uses AI to predict confirmations, find secret multi-modal connections, and book your backups automatically.
          </p>
          
          <div className="flex flex-col sm:flex-row justify-center items-center space-y-4 sm:space-y-0 sm:space-x-4">
            <Link to="/dashboard" className="w-full sm:w-auto bg-gradient-to-r from-blue-600 to-emerald-500 text-white px-8 py-4 rounded-full text-lg font-bold hover:shadow-[0_0_40px_rgba(16,185,129,0.3)] transition-all transform hover:-translate-y-1 flex items-center justify-center">
              <MessageSquare className="mr-2 h-5 w-5" />
              Start Chatting
            </Link>
          </div>
        </div>
      </div>

      {/* --- TRUSTED BY / INTEGRATIONS STRIP --- */}
      <div id="integrations" className="py-10 border-y border-white/5 bg-[#060A14]">
        <div className="max-w-7xl mx-auto px-6">
          <p className="text-center text-xs font-bold text-slate-500 uppercase tracking-widest mb-6">Powered by Industry Leaders</p>
          <div className="flex flex-wrap justify-center gap-8 md:gap-16 items-center opacity-50 grayscale hover:grayscale-0 transition-all duration-500">
            <span className="text-2xl font-black text-slate-300 flex items-center"><Train className="mr-2 text-blue-400"/> IRCTC Data</span>
            <span className="text-2xl font-black text-slate-300 flex items-center"><Plane className="mr-2 text-emerald-400"/> Google Flights</span>
            <span className="text-2xl font-black text-slate-300">Gemini AI</span>
            <span className="text-2xl font-black text-slate-300">Telegram APIs</span>
          </div>
        </div>
      </div>

      {/* --- HOW IT WORKS (Visual Steps) --- */}
      <div id="how-it-works" className="py-24 bg-[#0B1120]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">How Agentra works</h2>
            <p className="text-xl text-slate-400 font-light">Three simple steps to zero-stress travel.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-12 relative">
            {/* Connecting Line */}
            <div className="hidden md:block absolute top-12 left-[15%] right-[15%] h-0.5 bg-gradient-to-r from-blue-900 via-emerald-900 to-blue-900"></div>

            <div className="relative text-center z-10">
              <div className="w-24 h-24 mx-auto bg-slate-900 rounded-2xl shadow-2xl border border-slate-700 flex items-center justify-center mb-6 transform rotate-3 hover:rotate-0 transition-all">
                <MessageSquare className="w-10 h-10 text-blue-400" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-3">1. Tell us your plan</h3>
              <p className="text-slate-400 text-sm leading-relaxed">Just chat naturally. "I need to go from Gwalior to Ayodhya tomorrow night."</p>
            </div>

            <div className="relative text-center z-10">
              <div className="w-24 h-24 mx-auto bg-slate-900 rounded-2xl shadow-2xl border border-slate-700 flex items-center justify-center mb-6 -rotate-3 hover:rotate-0 transition-all">
                <Sparkles className="w-10 h-10 text-emerald-400" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-3">2. AI analyzes millions of routes</h3>
              <p className="text-slate-400 text-sm leading-relaxed">Our engine calculates waitlist probabilities and stitches together trains, cabs, and flights.</p>
            </div>

            <div className="relative text-center z-10">
              <div className="w-24 h-24 mx-auto bg-slate-900 rounded-2xl shadow-2xl border border-slate-700 flex items-center justify-center mb-6 rotate-3 hover:rotate-0 transition-all">
                <ShieldCheck className="w-10 h-10 text-blue-500" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-3">3. We secure your journey</h3>
              <p className="text-slate-400 text-sm leading-relaxed">Get automated Telegram alerts at T-24 and T-4 hours if your ticket needs a smart backup.</p>
            </div>
          </div>
        </div>
      </div>


    <FeatureShowcase />

      {/* --- FEATURES BENTO GRID --- */}
      <div id="features" className="py-24 bg-[#060A14]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            <div className="bg-slate-900/50 rounded-3xl p-10 border border-slate-800 hover:border-blue-500/30 hover:shadow-2xl hover:shadow-blue-500/10 transition-all group">
              <div className="bg-blue-500/10 w-16 h-16 rounded-2xl flex items-center justify-center mb-6 border border-blue-500/20">
                <MapPin className="text-blue-400 w-8 h-8 group-hover:scale-110 transition-transform" />
              </div>
              <h3 className="text-3xl font-bold text-white mb-4">Hub-and-Spoke Routing</h3>
              <p className="text-lg text-slate-400 mb-6 font-light">No direct trains? No problem. Agentra automatically finds intercity cabs to nearby major stations and connects you to confirmed trains.</p>
              <Link to="/dashboard" className="text-blue-400 font-bold flex items-center hover:text-blue-300">
                Try it now <ArrowRight className="ml-2 w-4 h-4" />
              </Link>
            </div>

            <div className="bg-slate-900/50 rounded-3xl p-10 border border-slate-800 hover:border-emerald-500/30 hover:shadow-2xl hover:shadow-emerald-500/10 transition-all group">
              <div className="bg-emerald-500/10 w-16 h-16 rounded-2xl flex items-center justify-center mb-6 border border-emerald-500/20">
                <Sparkles className="text-emerald-400 w-8 h-8 group-hover:scale-110 transition-transform" />
              </div>
              <h3 className="text-3xl font-bold text-white mb-4">Predictive WL Engine</h3>
              <p className="text-lg text-slate-400 mb-6 font-light">Why gamble with a Waitlist? Our AI evaluates API baselines to give you a realistic percentage of confirmation, saving you from last-minute stress.</p>
              <Link to="/dashboard" className="text-emerald-400 font-bold flex items-center hover:text-emerald-300">
                See predictions <ArrowRight className="ml-2 w-4 h-4" />
              </Link>
            </div>

          </div>
        </div>
      </div>

      {/* --- FOOTER --- */}
      <footer className="bg-[#0B1120] py-16 border-t border-white/10 text-slate-400">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-4 gap-10">
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center mb-6 space-x-3">
               <div className="bg-white p-1 rounded-lg">
                 <img src="logo2.png" alt="Agentra Logo" className="h-8 w-auto mix-blend-multiply" />
               </div>
               <span className="text-xl font-bold text-white tracking-wide">Agentra</span>
            </div>
            <p className="max-w-xs text-sm leading-relaxed font-light">
              Intelligent Travel. Limitless Possibilities. Agentra is the modern OS for the smart traveler.
            </p>
          </div>
          <div>
            <h4 className="text-white font-bold mb-4 tracking-wide text-sm uppercase">Product</h4>
            <ul className="space-y-3 text-sm">
              <li><a href="#" className="hover:text-emerald-400 transition">Smart Routing</a></li>
              <li><a href="#" className="hover:text-emerald-400 transition">WL Predictions</a></li>
              <li><a href="#" className="hover:text-emerald-400 transition">Telegram Alerts</a></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-bold mb-4 tracking-wide text-sm uppercase">Company</h4>
            <ul className="space-y-3 text-sm">
              <li><a href="#" className="hover:text-emerald-400 transition">About Us</a></li>
              <li><a href="#" className="hover:text-emerald-400 transition">Privacy Policy</a></li>
              <li><a href="#" className="hover:text-emerald-400 transition">Contact Support</a></li>
            </ul>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;