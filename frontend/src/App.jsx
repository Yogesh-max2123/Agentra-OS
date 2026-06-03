import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, useParams } from 'react-router-dom';
import { PlaneTakeoff, Train, Send, Bot, Clock, TerminalSquare, Sun, Moon, Map, ChevronRight, Loader2, CheckCircle2, Trash2, CalendarDays, Ticket, Database, Hotel, MapPin, Star, Building2, Coffee, ShieldCheck,TrainFront, Plane, CreditCard} from 'lucide-react';

import ItineraryViewer from './components/ItineraryViewer';

const getStatusBadgeStyle = (status) => {
  if (!status) return 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700';
  const s = status.toLowerCase();
  if (s.includes('regret') || s.includes('not avail') || s.includes('cancel') || s.includes('departed')) {
    return 'bg-red-50 text-red-600 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-800/50';
  }
  if (s.includes('avail')) {
    return 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-800/50';
  }
  if (s.includes('wl') || s.includes('rac')) {
    return 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-800/50';
  }
  return 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700';
};


// ==========================================
// SMART HOTEL IMAGE COMPONENT (With Pexels Fallback)
// ==========================================
const HotelImage = ({ hotelName, defaultImage, className }) => {
  const [imgSrc, setImgSrc] = useState(defaultImage);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    setImgSrc(defaultImage);
    setHasError(false);
  }, [defaultImage]);

  const handleError = async () => {
    if (hasError) return; // Infinite loop se bachne ke liye
    setHasError(true);
    
    try {
      const apiKey = import.meta.env.VITE_PEXELS_API_KEY || process.env.REACT_APP_PEXELS_API_KEY;
      const response = await fetch(`https://api.pexels.com/v1/search?query=${encodeURIComponent(hotelName + " hotel luxury exterior")}&per_page=1`, {
        headers: { Authorization: apiKey }
      });
      const data = await response.json();
      if (data.photos && data.photos.length > 0) {
        setImgSrc(data.photos[0].src.large);
      } else {
        setImgSrc(`https://loremflickr.com/800/600/hotel,building`);
      }
    } catch (err) {
      setImgSrc(`https://loremflickr.com/800/600/hotel,building`);
    }
  };

  return (
    <img 
      src={imgSrc || `https://loremflickr.com/800/600/hotel,building`} 
      alt={hotelName} 
      className={className}
      onError={handleError} // Agar default load nahi hui, toh Pexels trigger hoga
    />
  );
};

const loadState = (key, defaultValue) => {
  const saved = localStorage.getItem(key);
  if (saved) {
    try { return JSON.parse(saved); } catch (e) { return defaultValue; }
  }
  return defaultValue;
};

// ==========================================
// COMPONENT 1: THE MAIN CHATBOT INTERFACE
// ==========================================
function ChatInterface() {
  const [isDarkMode, setIsDarkMode] = useState(() => loadState('nexusTheme', true));
  const [input, setInput] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [hasResults, setHasResults] = useState(false);
  
  const [liveTrains, setLiveTrains] = useState([]);
  const [selectedTrain, setSelectedTrain] = useState(null);
  const [selectedCoach, setSelectedCoach] = useState(null); 
  const [smartChips, setSmartChips] = useState([]);

  // ACCOMMODATION STATE
  const [accommodationResults, setAccommodationResults] = useState(null);
  const [showAccommodations, setShowAccommodations] = useState(false);
  const [selectedHotel, setSelectedHotel] = useState(null); 
  const [bookingSuccessData, setBookingSuccessData] = useState(null);

  const [selectedRoomType, setSelectedRoomType] = useState(null);

  const [activeJourneys, setActiveJourneys] = useState(() => loadState('nexusVault', [])); 
  const [messages, setMessages] = useState(() => loadState('nexusMessages', [
    { sender: 'agent', text: 'Hello! I am Agentra, your AI Travel Orchestrator. Where would you like to travel today?' }
  ]));
  const [logs, setLogs] = useState(() => loadState('nexusLogs', [
    { time: new Date().toLocaleTimeString(), text: 'System initialized and connected to database.', type: 'success' }
  ]));

  const [activeTab, setActiveTab] = useState('planner');   
  const [dbBookings, setDbBookings] = useState([]);
  const [expandedBooking, setExpandedBooking] = useState(null);
  
  // 🚨 NEW STATE: For Itinerary Management
  const [currentPnr, setCurrentPnr] = useState(null);
  const [selectedTripPnr, setSelectedTripPnr] = useState(null); // Add this!

  const logsEndRef = useRef(null);
  const chatEndRef = useRef(null);

  useEffect(() => { localStorage.setItem('nexusTheme', JSON.stringify(isDarkMode)); }, [isDarkMode]);
  useEffect(() => { localStorage.setItem('nexusVault', JSON.stringify(activeJourneys)); }, [activeJourneys]);
  useEffect(() => { localStorage.setItem('nexusMessages', JSON.stringify(messages)); }, [messages]);
  useEffect(() => { localStorage.setItem('nexusLogs', JSON.stringify(logs)); }, [logs]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs, messages]);

  const addLog = (text, type = 'info') => {
    setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), text, type }]);
  };

  // 🚨 NAYA LOGIC: Reset Only Chat Context
  const handleClearChat = () => {
    setMessages([
      { sender: 'agent', text: 'Hello! I am Agentra, your AI Travel Orchestrator. Where would you like to travel today?' }
    ]);
    setLiveTrains([]);
    setAccommodationResults(null);
    setShowAccommodations(false);
    setSmartChips([]);
    setHasResults(false);
    setBookingSuccessData(null);
    setActiveTab('planner');
    addLog("Chat context cleared. Starting fresh.", "info");
  };

  const fetchBookings = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/bookings');
      if (res.ok) {
        const data = await res.json();
        setDbBookings(data.status === "success" ? data.data : []);
      }
    } catch (e) {
      setDbBookings([]); 
    }
  };

  useEffect(() => { fetchBookings(); }, []);

  const handleSend = async (e, chipText = null, hiddenQuery = null) => {
    if (e) e.preventDefault(); 
    
    const userQuery = hiddenQuery || chipText || input; 
    if (!userQuery.trim() || isSearching) return;

    const currentHistory = [...messages]; 

    if (!hiddenQuery) {
        setMessages(prev => [...prev, { sender: 'user', text: userQuery }]);
    }
    
    setInput(''); setIsSearching(true); setHasResults(false); setSmartChips([]); 
    addLog(`Sending query to FastAPI: "${userQuery.substring(0, 30)}..."`, 'waiting');

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userQuery, history: currentHistory, session_id: "guest_123" })
      });

      if (!response.ok) throw new Error(`Backend connection failed with status: ${response.status}`);
      const data = await response.json(); 

      data.logs.forEach(log => addLog(log.text, log.type));

      let cleanMessage = data.agent_message || "";
      
      // 🚆 PARSE TRAIN DRAFT
      const draftMatch = cleanMessage.match(/\[HIDDEN_DRAFT_ID:\s*(DRAFT_[A-Z0-9_]+)\]/i);
      if (draftMatch) {
          const draftId = draftMatch[1];
          cleanMessage = cleanMessage.replace(/\[HIDDEN_DRAFT_ID:.*?\]/i, '').trim();
          const draftPayload = data.action_data || { draft_id: draftId, passengers: "[]" };
          localStorage.setItem('nexusDraftData', JSON.stringify(draftPayload));
          const currentActiveTrain = activeJourneys[activeJourneys.length - 1] || null;
          localStorage.setItem('nexusActiveTrain', JSON.stringify(currentActiveTrain));
          addLog(`Draft Review generated. Opening Train Checkout tab.`, 'success');
          window.open(`/checkout/${draftId}`, '_blank');
      }

      // 🏨 PARSE HOTEL DRAFT
      const hotelDraftMatch = cleanMessage.match(/\[HIDDEN_HOTEL_DRAFT:\s*(HTL_DRAFT_[A-Z0-9_]+)\]/i);
      if (hotelDraftMatch) {
          const draftId = hotelDraftMatch[1];
          cleanMessage = cleanMessage.replace(/\[HIDDEN_HOTEL_DRAFT:.*?\]/i, '').trim();
          
          addLog(`Hotel locked! Opening Secure Hotel Checkout.`, 'success');
          window.open(`/hotel-checkout/${draftId}`, '_blank');
      }

      setMessages(prev => [...prev, { sender: 'agent', text: cleanMessage }]);
      
      if (data.results_ready) {
        setHasResults(true);
        if (data.action_data && data.action_data.type === "accommodations") {
          setAccommodationResults(data.action_data.data);
          setShowAccommodations(true);
          setLiveTrains([]); 
          setBookingSuccessData(null); 
          addLog("Accommodation Workspace Rendered.", "success");
        } 
        else if (data.action_data && (data.action_data.type === "trains" || data.action_data.type === "flights")) {
          setLiveTrains(data.action_data.data);
          setShowAccommodations(false); 
        }
        if (data.smart_chips) setSmartChips(data.smart_chips);
      }
    } catch (error) {
      addLog(`Error: ${error.message}`, 'error'); 
      setMessages(prev => [...prev, { sender: 'agent', text: "System Error: Cannot reach the backend API." }]);
    } finally {
      setIsSearching(false);
    }
  };

  // CROSS-TAB COMMUNICATION LISTENER
  useEffect(() => {
    const handleStorageChange = async (e) => {
      // Train Checkout Listener
      if (e.key === 'nexusPaymentSuccess' && e.newValue) {
        const payload = JSON.parse(e.newValue);
        const hiddenMessage = `SYSTEM_PAYMENT_SUCCESS_TRIGGER Mode:${payload.isFlight ? "FLIGHT" : "TRAIN"} | PNR:${payload.pnr} | CARRIER:${payload.trainName} | FROM:${payload.source} TO:${payload.dest} | TIMES:${payload.dep} to ${payload.arr} | CLASS:${payload.bookedClass} | TOTAL_AMOUNT:${payload.total_amount} | IS_SOLO:${payload.is_solo} | PASSENGERS:${JSON.stringify(payload.passengers)}`;
        handleSend(null, null, hiddenMessage);
        setTimeout(() => fetchBookings(), 3000); 
        localStorage.removeItem('nexusPaymentSuccess');
      }
      
      // 🚨 UPDATED: Hotel Checkout Listener
      if (e.key === 'nexusHotelPaymentSuccess' && e.newValue) {
        const payload = JSON.parse(e.newValue);
        addLog(`Hotel payment successful for Room: ${payload.room_no}`, 'success');
        
        setBookingSuccessData({ 
            name: payload.hotel_name, 
            ref: payload.stay_booking_id, 
            room: payload.room_no 
        });
        
        const hiddenMessage = `SYSTEM_STAY_BOOKED Confirmation Ref: ${payload.stay_booking_id}, Property: ${payload.hotel_name}, Room: ${payload.room_no}`;
        handleSend(null, null, hiddenMessage);
        
        // 🚨 NAYA LOGIC: Generate Itinerary Automatically
        const bookedPnr = payload.pnr || "UNKNOWN";
        setCurrentPnr(bookedPnr);
        addLog("Generating Smart AI Itinerary...", "waiting");
        
        try {
            await fetch(`http://localhost:8000/api/trips/${bookedPnr}/generate-itinerary`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pnr: bookedPnr,
                    purpose: "Explore the city", // This is generic; Agent backend prompt will handle details
                    duration_days: 2,
                    primary_location: "City Center"
                })
            });
            addLog("Smart Itinerary generated successfully!", "success");
            // Switch to the 'My Trips' tab automatically
            setActiveTab('trips');
            setSelectedTripPnr(bookedPnr);
        } catch (error) {
            addLog("Failed to auto-generate itinerary.", "error");
        }

        localStorage.removeItem('nexusHotelPaymentSuccess');
      }
    };
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [messages, isSearching]);
  
  const toggleTheme = () => setIsDarkMode(!isDarkMode);

  const getTopAvailability = (availObj) => {
    if (!availObj || Object.keys(availObj).length === 0) return null;
    const firstClass = Object.keys(availObj)[0];
    return { class: firstClass, ...availObj[firstClass] };
  };

  const handleLockHotel = (hotel) => {
    addLog(`Initiating draft simulation for ${hotel.name}...`, 'waiting');
    setSelectedHotel(null); 
    const autoQuery = `I have locked the ${journeyType}: ${selectedTrain.Train_Name} (${selectedTrain.Train_Number}) from ${selectedTrain.Source} to ${selectedTrain.Destination} ${bookableFare}. Please give me a quick price & delay analysis. DO NOT fetch weather or intel yet. Strictly STOP and just ask me if I want it.`;
    handleSend(null, null, autoQuery); 
  };

  return (
    <div className={`${isDarkMode ? 'dark' : ''} h-screen w-full font-sans overflow-hidden`}>
      <div className="flex h-full w-full bg-slate-50 dark:bg-[#0B1120] text-slate-900 dark:text-slate-100 transition-colors duration-300">
        
        {/* LEFT PANEL */}
        <div className="w-[35%] min-w-[380px] max-w-[450px] bg-white dark:bg-slate-900/80 border-r border-slate-200 dark:border-slate-800 flex flex-col shadow-2xl z-20 backdrop-blur-xl">
          <div className="bg-primary dark:bg-slate-950 text-white p-5 flex items-center justify-between border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="bg-secondary/20 text-blue-400 p-2.5 rounded-xl border border-blue-500/20 shadow-inner"><Bot size={22} /></div>
                  <div>
                    <h1 className="text-[17px] font-extrabold tracking-wide">Agentra OS</h1>
                    <p className="text-[10px] text-slate-400 font-bold tracking-widest uppercase mt-0.5">Transit Orchestrator</p>
                  </div>
                </div>
                
                {/* 🚨 NAYA CLEAR CHAT BUTTON YAHAN ADD HUA HAI */}
                <button 
                    onClick={handleClearChat}
                    title="Clear Chat History"
                    className="text-slate-500 hover:text-red-400 bg-slate-900/50 hover:bg-slate-800 p-2.5 rounded-xl transition-all border border-transparent hover:border-red-900/50"
                >
                    <Trash2 size={16} />
                </button>
              </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-6 bg-slate-50/50 dark:bg-transparent custom-scrollbar">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] p-4 rounded-2xl flex items-start gap-3 shadow-sm ${msg.sender === 'user' ? 'bg-secondary text-white rounded-br-sm' : 'bg-white dark:bg-slate-800/80 border border-slate-100 dark:border-slate-700/50 rounded-bl-sm text-slate-800 dark:text-slate-200'}`}>
                  {msg.sender === 'agent' && <Bot size={18} className="mt-0.5 flex-shrink-0 text-secondary dark:text-blue-400" />}
                  <p className="text-[14px] leading-relaxed font-medium whitespace-pre-line">{msg.text}</p>
                </div>
              </div>
            ))}
            
            {isSearching && (
              <div className="flex justify-start">
                <div className="bg-white dark:bg-slate-800/80 border border-slate-100 dark:border-slate-700/50 p-4 rounded-2xl rounded-bl-sm flex items-center gap-3">
                  <Bot size={18} className="text-secondary dark:text-blue-400" />
                  <div className="flex gap-1.5">
                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></span>
                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="p-4 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
            <form onSubmit={handleSend} className="relative flex items-center">
              <input type="text" value={input} onChange={(e) => setInput(e.target.value)} disabled={isSearching} placeholder={isSearching ? "Agent is processing..." : "Train/Flights from Delhi to Mumbai tommorow..."} className="w-full bg-slate-100 dark:bg-slate-950 border border-transparent dark:border-slate-800 rounded-2xl py-3.5 pl-5 pr-14 text-[14px] text-slate-800 dark:text-slate-200 outline-none focus:ring-1 focus:ring-blue-500 transition-all" />
              <button type="submit" disabled={isSearching || !input.trim()} className="absolute right-2 p-2.5 bg-secondary hover:bg-blue-600 text-white rounded-xl disabled:opacity-50 cursor-pointer transition-colors">
                <Send size={18} className="ml-0.5" />
              </button>
            </form>
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="flex-1 flex flex-col relative overflow-hidden bg-slate-50 dark:bg-[#0B1120] transition-colors duration-300">
          <div className="h-16 border-b border-slate-200 dark:border-slate-800/80 bg-white/80 dark:bg-slate-900/50 backdrop-blur-md flex items-center justify-between px-8 z-10 relative">
            <div className="flex gap-6 h-full">
              <button onClick={() => setActiveTab('planner')} className={`text-[14px] font-bold h-full flex items-center transition-all ${activeTab === 'planner' ? 'text-secondary border-b-2 border-secondary' : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'}`}>Planner View</button>
              <button onClick={() => setActiveTab('active')} className={`text-[14px] font-bold h-full flex items-center transition-all ${activeTab === 'active' ? 'text-secondary border-b-2 border-secondary' : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'}`}>Vault ({activeJourneys.length})</button>
              <button onClick={() => { setActiveTab('history'); fetchBookings(); }} className={`text-[14px] font-bold h-full flex items-center gap-2 transition-all ${activeTab === 'history' ? 'text-secondary border-b-2 border-secondary' : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'}`}>
                <CalendarDays size={16} /> My Bookings
              </button>
              
              {/* 🚨 NAYA TAB YAHAN ADD KIYA HAI */}
              <button onClick={() => setActiveTab('trips')} className={`text-[14px] font-bold h-full flex items-center gap-2 transition-all ${activeTab === 'trips' ? 'text-secondary border-b-2 border-secondary' : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'}`}>
                <Map size={16} /> My Trips
              </button>
            </div>
            <div className="flex items-center gap-5">
              <button onClick={toggleTheme} className="p-2 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-amber-300 bg-slate-100 dark:bg-slate-800 rounded-full transition-all">
                {isDarkMode ? <Sun size={18} /> : <Moon size={18} />}
              </button>
              <button onClick={() => { localStorage.clear(); window.location.reload(); }} className="text-[11px] font-bold tracking-wider text-red-500 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-800/50 px-3 py-1.5 rounded-full hover:bg-red-500 hover:text-white transition-all">
                RESET SYSTEM
              </button>
            </div>
          </div>

          <div className="flex-1 p-8 overflow-y-auto custom-scrollbar flex flex-col">
            <div className="mb-8">
              <h2 className="text-2xl font-extrabold text-slate-800 dark:text-slate-100 tracking-tight flex items-center gap-2">
                {activeTab === 'planner' ? 'Current Iteration' : activeTab === 'active' ? 'Your Vault' : activeTab === 'trips' ? 'Smart Itinerary' : 'Database: Past Bookings'} 
                {isSearching && activeTab === 'planner' && <Loader2 size={20} className="animate-spin text-secondary ml-2" />}
              </h2>
              <p className="text-slate-500 dark:text-slate-400 text-[14px] mt-1">
                {activeTab === 'history' ? "All your historically confirmed tickets managed by Agentra." : activeTab === 'active' ? "Review and manage your locked travel deployments." : activeTab === 'trips' ? "Your AI-crafted personalized city exploration plan." : (isSearching ? "Aggregating multi-modal transit data..." : hasResults ? "Analysis complete. Displaying optimal outputs." : "Awaiting user parameters to begin analysis.")}
              </p>
            </div>

            <div className="flex-1">



              {/* 🚨 VAULT RENDER BLOCK (PASTE YAHAN KARNA HAI) */}
              {activeTab === 'active' && (
                <div className="flex-1 overflow-y-auto custom-scrollbar animate-in fade-in duration-300 p-8">
                  {/*<div className="mb-8">
                    <h2 className="text-2xl font-extrabold text-slate-800 dark:text-slate-100 tracking-tight flex items-center gap-2">
                      Your Vault
                    </h2>
                    <p className="text-slate-500 dark:text-slate-400 text-[14px] mt-1">
                      Review and manage your locked travel deployments.
                    </p>
                  </div>*/}

                  {activeJourneys.length === 0 ? (
                    <div className="h-64 flex flex-col items-center justify-center text-slate-400 dark:text-slate-600 opacity-60">
                      <TrainFront size={48} className="mb-4" strokeWidth={1.5} />
                      <p className="text-lg font-bold">Your Vault is Empty</p>
                      <p className="text-sm">Search and lock a journey to see it here.</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 gap-6">
                      {activeJourneys.map((journey, idx) => (
                        <div key={idx} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 relative overflow-hidden group hover:border-slate-300 dark:hover:border-slate-700 transition-all shadow-sm">
                          
                          <div className={`absolute top-0 left-0 w-1 h-full ${journey.is_flight ? 'bg-indigo-500' : 'bg-blue-500'}`}></div>
                          
                          <div className="flex justify-between items-start mb-4">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                {journey.is_flight ? <Plane size={20} className="text-indigo-500 dark:text-indigo-400" /> : <TrainFront size={20} className="text-blue-500 dark:text-blue-400" />}
                                <h3 className="text-lg font-black text-slate-800 dark:text-white">{journey.Train_Name || journey.airline || 'Unknown Journey'}</h3>
                              </div>
                              <p className="text-sm font-bold text-slate-500 dark:text-slate-400">{journey.Train_Number || journey.flight_number || 'N/A'}</p>
                            </div>
                            
                            <div className="flex items-center gap-2">
                              <span className={`px-3 py-1 text-[11px] font-black uppercase tracking-wider rounded-lg border ${getStatusBadgeStyle(journey.bookedStatus)}`}>
                                {journey.bookedStatus ? String(journey.bookedStatus) : 'STATUS UNAVAILABLE'}
                              </span>
                              <button 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveJourneys(prev => prev.filter((_, i) => i !== idx));
                                }} 
                                className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                                title="Remove from Vault"
                              >
                                <Trash2 size={16} />
                              </button>
                            </div>
                          </div>

                          <div className="flex items-center gap-6 mb-6 p-4 bg-slate-50 dark:bg-slate-950/50 rounded-xl border border-slate-100 dark:border-slate-800/50">
                            <div className="flex-1">
                              <p className="text-2xl font-black text-slate-800 dark:text-white">{journey.Departure || '--:--'}</p>
                              <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">{journey.Source || 'SRC'}</p>
                            </div>
                            
                            <div className="flex-1 flex flex-col items-center justify-center">
                              <p className="text-xs font-bold text-slate-400 mb-1">{journey.Travel_Time || 'N/A'}</p>
                              <div className="w-full h-0.5 bg-slate-200 dark:bg-slate-800 relative">
                                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500 bg-slate-50 dark:bg-slate-950 px-2">
                                  <Clock size={14} />
                                </div>
                              </div>
                            </div>

                            <div className="flex-1 text-right">
                              <p className="text-2xl font-black text-slate-800 dark:text-white">{journey.Arrival || '--:--'}</p>
                              <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">{journey.Destination || 'DST'}</p>
                            </div>
                          </div>

                          <div className="flex justify-between items-end border-t border-slate-100 dark:border-slate-800 pt-5">
                            <div>
                              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Selected Class & Fare</p>
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-black text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-500/10 px-2 py-0.5 rounded">{journey.bookedClass || 'N/A'}</span>
                                <span className="text-xl font-black text-slate-800 dark:text-white">₹{journey.bookedFare || 'N/A'}</span>
                              </div>
                            </div>
                            
                            {/*<button 
                              onClick={() => {
                                  const passengers = [{name: "", age: ""}];
                                  if (journey.is_flight) {
                                    localStorage.setItem('nexusFlightDraftData', JSON.stringify({
                                        airline: journey.airline,
                                        flight_number: journey.flight_number,
                                        source: journey.Source,
                                        destination: journey.Destination,
                                        seat_class: journey.bookedClass,
                                        price: journey.bookedFare,
                                        passengers: passengers
                                    }));
                                    window.open(`/flight-checkout/${journey.flight_number}`, '_blank');
                                  } else {
                                    localStorage.setItem('nexusTrainDraftData', JSON.stringify({
                                        train_name: journey.Train_Name,
                                        train_number: journey.Train_Number,
                                        source: journey.Source,
                                        destination: journey.Destination,
                                        coach: journey.bookedClass,
                                        price: journey.bookedFare,
                                        passengers: passengers
                                    }));
                                    window.open(`/train-checkout/${journey.Train_Number}`, '_blank');
                                  }
                              }}
                              className={`${journey.is_flight ? 'bg-indigo-600 hover:bg-indigo-500' : 'bg-blue-600 hover:bg-blue-500'} text-white px-6 py-2.5 rounded-xl font-black transition-all flex items-center gap-2 text-sm shadow-lg`}
                            >
                              <CreditCard size={16} /> Deploy & Pay
                            </button>
                            */}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {/* 🚨 VAULT RENDER BLOCK ENDS HERE */}

              {/* 🚨 UPDATED RENDER BLOCK: TRIPS DASHBOARD & ITINERARY VIEWER */}
              {activeTab === 'trips' && (
                  <div className="h-full flex flex-col animate-in fade-in duration-300">
                      
                      {/* DASHBOARD LIST VIEW (If no specific trip is selected) */}
                      {!selectedTripPnr ? (
                          <div className="flex-1">
                              <div className="flex justify-between items-center mb-6">
                                  <h2 className="text-xl font-extrabold text-slate-800 dark:text-white">Your Travel Archives</h2>
                              </div>
                              
                              {/* Filter only Completed bookings that actually have itinerary_data */}
                              {dbBookings.filter(b => b.status === "Completed" && b.itinerary_data).length > 0 ? (
                                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                      {dbBookings.filter(b => b.status === "Completed" && b.itinerary_data).map((trip, idx) => {
                                          const destCity = trip.journey ? trip.journey.split(" to ")[1].split(",")[0].trim() : "Unknown City";
                                          const travelDate = trip.departure_time ? new Date(trip.departure_time).toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' }) : "Date Unknown";
                                          
                                          return (
                                              <div 
                                                key={idx} 
                                                onClick={() => setSelectedTripPnr(trip.pnr)} 
                                                className="bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 p-5 rounded-2xl cursor-pointer hover:border-blue-500 hover:shadow-lg hover:shadow-blue-500/10 transition-all flex justify-between items-center group"
                                              >
                                                  <div className="flex items-center gap-4">
                                                      <div className="w-12 h-12 bg-blue-50 dark:bg-blue-500/20 text-blue-500 dark:text-blue-400 rounded-xl flex items-center justify-center shrink-0">
                                                          <Map size={24} />
                                                      </div>
                                                      <div>
                                                          <h3 className="font-bold text-slate-800 dark:text-white text-lg">{destCity} Expedition</h3>
                                                          <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-0.5">{travelDate} • PNR: <span className="font-mono">{trip.pnr}</span></p>
                                                      </div>
                                                  </div>
                                                  <div className="flex items-center gap-2 shrink-0">
                                                  <button 
                                                      onClick={async (e) => {
                                                          e.stopPropagation(); 
                                                          setDbBookings(prev => prev.filter(b => b.pnr !== trip.pnr));
                                                          try { await fetch(`http://localhost:8000/api/bookings/${trip.pnr}`, { method: 'DELETE' }); } catch(err){}
                                                      }}
                                                      className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-500/10 rounded-xl transition-all opacity-0 group-hover:opacity-100"
                                                  >
                                                      <Trash2 size={18} />
                                                  </button>
                                                  <ChevronRight className="text-slate-400 group-hover:text-blue-500 transition-colors" />
                                                </div>
                                              </div>
                                          );
                                      })}
                                  </div>
                              ) : (
                                  <div className="h-64 flex flex-col items-center justify-center text-slate-400 dark:text-slate-600 opacity-60">
                                      <Map size={48} className="mb-4" strokeWidth={1.5} />
                                      <p className="text-lg font-bold">No Generated Itineraries</p>
                                      <p className="text-sm">Book a hotel to auto-generate a smart itinerary.</p>
                                  </div>
                              )}
                          </div>
                      ) : (
                          /* DETAIL ITINERARY VIEW */
                          <div className="flex flex-col h-full overflow-hidden">
                              <div className="flex items-center gap-4 mb-4 pb-4 border-b border-slate-200 dark:border-slate-800 shrink-0">
                                  <button 
                                      onClick={() => setSelectedTripPnr(null)}
                                      className="flex items-center gap-1.5 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white transition-colors font-bold text-sm bg-slate-100 dark:bg-slate-800 px-3 py-2 rounded-lg"
                                  >
                                      <ChevronRight className="rotate-180 shrink-0" size={16} /> Dashboard
                                  </button>
                                  <div className="h-6 w-px bg-slate-200 dark:bg-slate-700"></div>
                                  <span className="text-sm font-bold text-slate-400 font-mono tracking-wide">PNR: {selectedTripPnr}</span>
                              </div>
                              
                              <div className="flex-1 overflow-y-auto custom-scrollbar pr-2">
                                  <ItineraryViewer pnr={selectedTripPnr} />
                              </div>
                          </div>
                      )}
                  </div>
              )}


              

              {/* TAB 1: PLANNER VIEW */}
              {activeTab === 'planner' && (
                <>
                  {!hasResults && !isSearching ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-400 dark:text-slate-600 opacity-60 mt-10">
                      <Map size={64} className="mb-4" strokeWidth={1} />
                      <p className="text-lg font-medium">Workspace is empty</p>
                      <p className="text-sm">Initiate a query in the chat to generate routes.</p>
                    </div>
                  ) : (
                    <div className={`transition-all duration-700 ${isSearching ? 'opacity-30 blur-[2px] pointer-events-none scale-[0.98]' : 'opacity-100 scale-100'}`}>
                      
                      {/* 🏨 RENDER HOTELS/RETIRING ROOMS IF ACTIVE */}
                      {showAccommodations && accommodationResults && !bookingSuccessData && (
                        <div className="space-y-6">
                           <div className="bg-blue-500/10 border border-blue-500/20 p-5 rounded-2xl flex items-start gap-4">
                              <Hotel className="text-blue-400 shrink-0 mt-1" size={24}/>
                              <div>
                                 <h3 className="text-lg font-bold text-white tracking-wide">Agentra Diagnostics: {accommodationResults.recommended_type === 'RETIRING_ROOM' ? 'Transit Stay Optimal' : 'City Stay Optimal'}</h3>
                                 <p className="text-slate-400 text-sm mt-1">{accommodationResults.reasoning}</p>
                              </div>
                           </div>
                           
                           {/* SAFE RENDERING CHECK */}
                           {accommodationResults.options && accommodationResults.options.length > 0 ? (
                               <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                  {accommodationResults.options.map(opt => (
                                     <div key={opt.id} className="bg-slate-800/80 border border-slate-700 rounded-3xl overflow-hidden shadow-xl hover:border-blue-500/50 transition-all group flex flex-col">
                                        <div className="relative h-48 w-full overflow-hidden">
                                           <HotelImage hotelName={opt.name} defaultImage={opt.image} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                                           <div className="absolute top-3 right-3 bg-black/70 backdrop-blur-md px-3 py-1 rounded-full text-xs font-bold text-yellow-400 flex items-center gap-1">
                                              <Star size={12} className="fill-yellow-400" /> {opt.rating}
                                           </div>
                                        </div>
                                        <div className="p-5 flex-1 flex flex-col justify-between">
                                           <div>
                                              <h4 className="text-lg font-extrabold text-white mb-2 leading-tight">{opt.name}</h4>
                                              <p className="text-sm font-semibold text-slate-400 flex items-center gap-1.5"><MapPin size={14} className="text-blue-400" /> {opt.distance}</p>
                                           </div>
                                           <div className="mt-6 flex items-end justify-between">
                                              <div>
                                                 <p className="text-[10px] text-slate-500 uppercase font-black tracking-wider mb-0.5">Tariff</p>
                                                 <p className="text-2xl font-black text-emerald-400">₹{opt.price}</p>
                                              </div>
                                              <button onClick={() => {setSelectedHotel(opt);
                                                setSelectedRoomType(null);
                                              }} className="bg-slate-700 hover:bg-slate-600 text-white font-bold py-2.5 px-5 rounded-xl border border-slate-600 transition-all text-sm flex items-center gap-2">
                                                 Details <ChevronRight size={16}/>
                                              </button>
                                           </div>
                                        </div>
                                     </div>
                                  ))}
                               </div>
                           ) : (
                               <div className="bg-slate-800/50 border border-slate-700 p-8 rounded-3xl text-center">
                                   <p className="text-slate-400 text-lg font-bold">No properties available near this location right now.</p>
                               </div>
                           )}
                        </div>
                      )}

              
              
                      
  
                      {/* 🎉 SUCCESS STATE FOR ACCOMMODATIONS */}
                      {showAccommodations && bookingSuccessData && (
                        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-3xl p-10 text-center animate-in zoom-in-95 duration-500 max-w-2xl mx-auto mt-10">
                           <div className="w-20 h-20 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto mb-6 shadow-[0_0_30px_rgba(16,185,129,0.2)]">
                              <CheckCircle2 size={40} />
                           </div>
                           <h2 className="text-3xl font-black text-white mb-3">Stay Secured!</h2>
                           <p className="text-slate-400 text-lg mb-8">Your post-arrival accommodation is ready.</p>
                           
                           <div className="bg-slate-900/80 border border-slate-700/50 p-6 rounded-2xl flex flex-col gap-4 text-left">
                              <div className="flex justify-between items-center border-b border-slate-800 pb-4">
                                 <span className="text-slate-500 font-bold uppercase text-xs tracking-wider">Property</span>
                                 <span className="text-white font-bold text-lg">{bookingSuccessData.name}</span>
                              </div>
                              <div className="flex justify-between items-center border-b border-slate-800 pb-4">
                                 <span className="text-slate-500 font-bold uppercase text-xs tracking-wider">Room Allocation</span>
                                 <span className="text-emerald-400 font-black text-xl">{bookingSuccessData.room}</span>
                              </div>
                              <div className="flex justify-between items-center">
                                 <span className="text-slate-500 font-bold uppercase text-xs tracking-wider">Reference</span>
                                 <span className="text-slate-300 font-mono text-sm bg-slate-800 px-3 py-1 rounded-md">{bookingSuccessData.ref}</span>
                              </div>
                           </div>
                           <p className="text-xs text-slate-500 mt-6 font-bold tracking-wide">A detailed confirmation has been synced to your Telegram account.</p>
                        </div>
                      )}

                      {/* 🚆 RENDER TRAINS/FLIGHTS IF ACTIVE */}
                      {!showAccommodations && (
                        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                        {liveTrains.map((train, idx) => {
                          const topAvail = getTopAvailability(train.Availability_and_Fares);
                          return (
                            <div key={idx} className={`group bg-white dark:bg-slate-800/80 p-6 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700/80 flex flex-col gap-5 hover:shadow-xl transition-all cursor-pointer ${train.is_flight ? 'hover:border-indigo-500/50' : 'hover:border-secondary/50'}`}>
                              <div className="flex justify-between items-center">
                                <div className="flex items-center gap-3 text-slate-800 dark:text-slate-200 font-bold text-lg">
                                  <div className={`p-2.5 rounded-xl flex-shrink-0 ${train.is_flight ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-500' : 'bg-blue-50 dark:bg-blue-900/30 text-secondary'}`}>
                                    {train.is_flight ? <PlaneTakeoff size={22} /> : <Train size={22} />}
                                  </div>
                                  <div className="truncate max-w-[180px]" title={train.Train_Name}>{train.Train_Name}</div>
                                </div>
                                {topAvail ? (
                                  <span className={`flex items-center gap-1.5 text-[11px] font-bold px-3 py-1.5 rounded-full border flex-shrink-0 ${getStatusBadgeStyle(topAvail.status)}`}>
                                    <CheckCircle2 size={13} /> {topAvail.class}: ₹{topAvail.fare !== 'N/A' ? topAvail.fare : '---'}
                                  </span>
                                ) : (
                                  <span className="flex items-center gap-1.5 text-[11px] font-bold px-3 py-1.5 bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 rounded-full border border-slate-200 dark:border-slate-700 flex-shrink-0">Data Unavailable</span>
                                )}
                              </div>
                              <div className="flex justify-between items-center mt-3">
                                <div className="text-center w-16">
                                  <p className="font-extrabold text-2xl text-slate-800 dark:text-slate-100">{train.Departure}</p>
                                  <p className="text-slate-500 dark:text-slate-400 font-bold tracking-wider text-xs mt-1">{train.Source}</p>
                                </div>
                                <div className="flex-1 border-t-2 border-dashed border-slate-300 dark:border-slate-600 mx-4 relative">
                                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-white dark:bg-slate-800 px-3 py-0.5 rounded-full border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 text-[11px] font-bold flex items-center gap-1.5 shadow-sm whitespace-nowrap">
                                    <Clock size={12} /> {train.Travel_Time}
                                  </div>
                                </div>
                                <div className="text-center w-16">
                                  <p className="font-extrabold text-2xl text-slate-800 dark:text-slate-100">{train.Arrival}</p>
                                  <p className="text-slate-500 dark:text-slate-400 font-bold tracking-wider text-xs mt-1">{train.Destination}</p>
                                </div>
                              </div>
                              <div className="flex justify-between items-center mt-2 px-1">
                                <span className="text-xs font-semibold text-slate-400">{train.is_flight ? 'Flight' : 'No.'} {train.Train_Number}</span>
                                <button onClick={() => setSelectedTrain(train)} className={`py-2 px-4 text-white border-transparent rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-lg ${train.is_flight ? 'bg-indigo-500 hover:bg-indigo-400 shadow-indigo-500/30' : 'bg-blue-600 hover:bg-blue-500 shadow-blue-500/30'}`}>
                                  Details <ChevronRight size={14} />
                                </button>
                              </div>
                            </div>
                          );
                        })}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
              {/* 🚨 NAYA BLOCK: MY BOOKINGS (HISTORY) */}
              {activeTab === 'history' && (
                <div className="flex-1 overflow-y-auto custom-scrollbar animate-in fade-in duration-300 p-8">
                  <div className="mb-8">
                    <h2 className="text-2xl font-extrabold text-slate-800 dark:text-slate-100 tracking-tight">Database: Past Bookings</h2>
                    <p className="text-slate-500 dark:text-slate-400 text-[14px] mt-1">All your historically confirmed tickets managed by Agentra.</p>
                  </div>

                  {dbBookings.length === 0 ? (
                    <div className="h-64 flex flex-col items-center justify-center text-slate-400 dark:text-slate-600 opacity-60">
                      <CalendarDays size={48} className="mb-4" strokeWidth={1.5} />
                      <p className="text-lg font-bold">No Past Bookings</p>
                      <p className="text-sm">Your confirmed tickets will appear here.</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                      {dbBookings.map((booking, idx) => (
                        <div key={idx} className="bg-white dark:bg-slate-800/80 p-6 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700/80 flex flex-col gap-4 relative group">
                          
                          {/* DELETE BUTTON */}
                          <button 
                            onClick={async (e) => {
                                e.stopPropagation();
                                setDbBookings(prev => prev.filter(b => b.pnr !== booking.pnr));
                                try { await fetch(`http://localhost:8000/api/bookings/${booking.pnr}`, { method: 'DELETE' }); } catch(err){}
                            }}
                            className="absolute top-4 right-4 p-2 text-slate-400 hover:text-red-500 hover:bg-red-500/10 rounded-xl transition-all opacity-0 group-hover:opacity-100"
                            title="Delete Booking"
                          >
                            <Trash2 size={18} />
                          </button>
                          
                          <div className="flex items-center gap-3">
                            <div className="w-12 h-12 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-500 rounded-xl flex items-center justify-center shrink-0">
                              <Ticket size={24} />
                            </div>
                            <div>
                              <p className="text-xs font-bold text-slate-500 tracking-widest uppercase">PNR: {booking.pnr}</p>
                              <p className="text-lg font-black text-slate-800 dark:text-white">{booking.passenger_name} <span className="text-sm font-semibold text-slate-400">({booking.is_solo ? 'Solo' : 'Group'})</span></p>
                            </div>
                          </div>
                          
                          <div className="bg-slate-50 dark:bg-slate-900/50 p-4 rounded-xl border border-slate-100 dark:border-slate-800">
                            <p className="text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">{booking.journey}</p>
                            <div className="flex justify-between items-center text-xs font-semibold text-slate-500">
                              <span>Dep: {booking.departure_time ? new Date(booking.departure_time).toLocaleString() : 'N/A'}</span>
                              <span className="text-emerald-500 font-black text-sm">₹{booking.total_amount}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* TERMINAL */}
            <div className="mt-8 bg-slate-900 dark:bg-black/50 rounded-2xl p-5 text-slate-300 font-mono text-[13px] shadow-2xl border border-slate-800 h-48 flex flex-col flex-shrink-0">
              <div className="flex items-center gap-2 mb-3 text-slate-400 border-b border-slate-800 pb-3">
                <TerminalSquare size={16} /> 
                <span className="font-bold tracking-wider text-[11px] uppercase">Agentra Execution Logs</span>
              </div>
              <div className="overflow-y-auto space-y-2 flex-1 custom-scrollbar pr-2">
                {logs.map((log, idx) => (
                  <div key={idx} className="flex gap-4 opacity-90">
                    <span className="text-slate-600 shrink-0">[{log.time}]</span>
                    <span className={log.type === 'success' ? 'text-emerald-400' : log.type === 'waiting' ? 'text-amber-400 animate-pulse' : log.type === 'error' ? 'text-red-400' : 'text-slate-300'}>{log.type === 'waiting' ? '...' : '>'} {log.text}</span>
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 🚨 DYNAMIC DETAILS MODAL FOR HOTELS 🚨 */}
      {selectedHotel && (
        <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200" onClick={() => { setSelectedHotel(null); setSelectedRoomType(null); }}>
          <div className="bg-[#0B1120] rounded-3xl w-full max-w-lg shadow-2xl border border-slate-700 overflow-hidden flex flex-col max-h-[90vh]" onClick={e => e.stopPropagation()}>
            
            <div className="relative h-56 w-full shrink-0">
               <HotelImage hotelName={selectedHotel.name} defaultImage={selectedHotel.image} className="w-full h-full object-cover" />
               <button onClick={() => { setSelectedHotel(null); setSelectedRoomType(null); }} className="absolute top-4 right-4 text-white bg-black/50 hover:bg-black/80 p-2 rounded-full backdrop-blur-sm transition-all">✕</button>
               <div className="absolute bottom-4 left-4 bg-black/80 backdrop-blur-md px-4 py-2 rounded-xl flex items-center gap-3">
                  <span className="text-lg font-black text-white">{selectedHotel.name}</span>
                  <span className="text-xs font-bold text-yellow-400 bg-yellow-400/10 px-2 py-1 rounded-md flex items-center gap-1"><Star size={12} className="fill-yellow-400" /> {selectedHotel.rating}</span>
               </div>
            </div>

            <div className="p-6 overflow-y-auto custom-scrollbar">
              <div className="flex flex-wrap gap-2 mb-6">
                 {selectedHotel.amenities?.map((amenity, i) => (
                    <span key={i} className="text-xs font-bold text-blue-400 bg-blue-400/10 border border-blue-400/20 px-3 py-1.5 rounded-full">{amenity}</span>
                 ))}
              </div>

              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Select Room Classification</h4>
              <div className="space-y-3 mb-4">
                 {selectedHotel.rooms?.map((room, idx) => {
                    const isSelected = selectedRoomType?.type === room.type;
                    return (
                       <div key={idx} onClick={() => setSelectedRoomType(room)} className={`flex items-center justify-between p-4 rounded-2xl border transition-all cursor-pointer ${isSelected ? 'bg-blue-600/10 border-blue-500 ring-1 ring-blue-500' : 'bg-slate-800/50 border-slate-700 hover:bg-slate-800'}`}>
                          <div>
                             <span className={`font-bold text-lg ${isSelected ? 'text-blue-400' : 'text-slate-200'}`}>{room.type}</span>
                             <p className="text-[10px] uppercase font-bold text-emerald-400 mt-1">{room.status}</p>
                          </div>
                          <div className="flex items-center gap-4">
                             <span className="font-black text-xl text-white">₹{room.price}</span>
                             <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${isSelected ? 'border-blue-500' : 'border-slate-500'}`}>
                                {isSelected && <div className="w-2.5 h-2.5 rounded-full bg-blue-500" />}
                             </div>
                          </div>
                       </div>
                    )
                 })}
              </div>
            </div>

            <div className="p-5 bg-slate-900 border-t border-slate-800 shrink-0">
               <button 
                  onClick={() => {
                     if(!selectedRoomType) return;
                     addLog(`Initiating draft for ${selectedHotel.name} (${selectedRoomType.type})...`, 'waiting');

                     const activePnr = activeJourneys.length > 0 ? activeJourneys[activeJourneys.length - 1].pnr : "CAB9998887";
                     const payload = {
                         hotel_name: selectedHotel.name,
                         room_type: selectedRoomType.type,
                         price: selectedRoomType.price,
                         pnr: activePnr
                     };
                     localStorage.setItem('nexusHotelDraftData', JSON.stringify(payload));

                     setSelectedHotel(null);

                     const autoQuery = `SYSTEM_HOTEL_DRAFT_TRIGGER: Execute create_hotel_draft for hotel "${selectedHotel.name}", room "${selectedRoomType.type}", price ${selectedRoomType.price}. YOU MUST REPLY EXACTLY WITH THIS TEXT: "📋 Hotel Draft Ready\n[HIDDEN_HOTEL_DRAFT: <insert_draft_id_from_tool>]"`;
                     handleSend(null, null, autoQuery);
                  }} 
                  disabled={!selectedRoomType}
                  className={`w-full py-4 font-black rounded-xl transition-all shadow-lg text-lg ${!selectedRoomType ? 'bg-slate-800 text-slate-500 cursor-not-allowed shadow-none' : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-600/30'}`}
               >
                  {selectedRoomType ? `Lock ${selectedRoomType.type} & Proceed` : 'Select a Room to Continue'}
               </button>
            </div>
          </div>
        </div>
      )}

      {/* DYNAMIC DETAILS MODAL FOR TRAINS/FLIGHTS */}
      {selectedTrain && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md z-50 flex items-center justify-center p-4 animate-in fade-in duration-200" onClick={() => setSelectedTrain(null)}>
          <div className="bg-white dark:bg-[#0B1120] rounded-3xl w-full max-w-md shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col max-h-[90vh]" onClick={e => e.stopPropagation()}>
            <div className="bg-slate-50 dark:bg-slate-900 p-6 border-b border-slate-200 dark:border-slate-800 flex justify-between items-start flex-shrink-0">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`p-1.5 rounded-lg ${selectedTrain.is_flight ? 'bg-indigo-500/20 text-indigo-500 dark:text-indigo-400' : 'bg-secondary/20 text-blue-500 dark:text-blue-400'}`}>{selectedTrain.is_flight ? <PlaneTakeoff size={18} /> : <Train size={18} />}</span>
                  <h3 className="text-xl font-extrabold text-slate-800 dark:text-white">{selectedTrain.Train_Name}</h3>
                </div>
                <p className="text-slate-500 dark:text-slate-400 text-sm font-semibold ml-9">{selectedTrain.is_flight ? 'Flight' : 'Train No.'} {selectedTrain.Train_Number}</p>
              </div>
              <button onClick={() => setSelectedTrain(null)} className="text-slate-400 hover:text-white bg-slate-800 p-2 rounded-full transition-all">✕</button>
            </div>

            <div className="p-6 overflow-y-auto custom-scrollbar flex-1">
              <div className="flex justify-between items-center mb-8 relative">
                <div className="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 w-[60%] border-t-2 border-dashed border-slate-300 dark:border-slate-700"></div>
                <div className="text-center relative z-10 bg-white dark:bg-[#0B1120] px-2">
                  <p className="text-3xl font-black text-slate-800 dark:text-white">{selectedTrain.Departure}</p>
                  <p className={`font-bold mt-1 ${selectedTrain.is_flight ? 'text-indigo-500' : 'text-secondary'}`}>{selectedTrain.Source}</p>
                </div>
                <div className="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 bg-slate-100 dark:bg-slate-800 px-3 py-1 rounded-full text-xs font-bold text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700">{selectedTrain.Travel_Time}</div>
                <div className="text-center relative z-10 bg-white dark:bg-[#0B1120] px-2">
                  <p className="text-3xl font-black text-slate-800 dark:text-white">{selectedTrain.Arrival}</p>
                  <p className={`font-bold mt-1 ${selectedTrain.is_flight ? 'text-indigo-500' : 'text-secondary'}`}>{selectedTrain.Destination}</p>
                </div>
              </div>

              <h4 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">{selectedTrain.is_flight ? 'Select Class & Fares' : 'Select Seat Metrics & Fares'}</h4>
              <div className="space-y-3">
                {Object.entries(selectedTrain.Availability_and_Fares).map(([coach, data], i) => {
                  const s = data.status.toLowerCase();
                  const isUnavailable = s.includes('regret') || s.includes('not avail') || s.includes('cancel') || s.includes('departed');
                  const isSelected = selectedCoach === coach;
                  const showDetailText = data.prediction && (selectedTrain.is_flight || s.includes('wl') || s.includes('rac')); 
                  
                  return (
                    <div key={i} onClick={() => !isUnavailable && setSelectedCoach(coach)} className={`flex items-center justify-between p-3 rounded-xl border transition-all ${isUnavailable ? 'opacity-50 cursor-not-allowed bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800' : isSelected ? selectedTrain.is_flight ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-500 ring-1 ring-indigo-500 cursor-pointer' : 'bg-blue-50 dark:bg-blue-900/20 border-blue-500 ring-1 ring-blue-500 cursor-pointer' : 'bg-white dark:bg-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800 border-slate-200 dark:border-slate-700 cursor-pointer'}`}>
                      <div className="flex items-center gap-3">
                        <span className={`font-bold text-lg ${isSelected ? (selectedTrain.is_flight ? 'text-indigo-600 dark:text-indigo-400' : 'text-blue-600 dark:text-blue-400') : 'text-slate-700 dark:text-slate-200'}`}>{coach}</span>
                        <div className="flex flex-col">
                          <span className={`text-sm font-semibold px-2 py-0.5 rounded w-max border ${getStatusBadgeStyle(data.status)}`}>{data.status}</span>
                          {showDetailText && <span className="text-[10px] font-bold text-slate-400 mt-1 ml-1">{selectedTrain.is_flight ? `Route: ${data.prediction}` : `Prediction: ${data.prediction}`}</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`font-bold ${isSelected ? (selectedTrain.is_flight ? 'text-indigo-600 dark:text-indigo-400' : 'text-blue-600 dark:text-blue-400') : 'text-slate-800 dark:text-white'}`}>{data.fare !== 'N/A' ? `₹${data.fare}` : '---'}</span>
                        {!isUnavailable && <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${isSelected ? (selectedTrain.is_flight ? 'border-indigo-500' : 'border-blue-500') : 'border-slate-300 dark:border-slate-600'}`}>{isSelected && <div className={`w-2 h-2 rounded-full ${selectedTrain.is_flight ? 'bg-indigo-500' : 'bg-blue-500'}`} />}</div>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            
            <div className="p-4 bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 flex-shrink-0">
              {(() => {
                const isCompletelyUnavailable = Object.values(selectedTrain.Availability_and_Fares).every(data => {
                  const s = data.status.toLowerCase();
                  return s.includes('regret') || s.includes('not avail') || s.includes('cancel') || s.includes('departed');
                });
                const canBook = selectedCoach !== null && !isCompletelyUnavailable;
                return (
                  <button onClick={() => {
                      if (!canBook) return;
                      const coachData = selectedTrain.Availability_and_Fares[selectedCoach];
                      const ticketRecord = { ...selectedTrain, bookingDate: new Date().toLocaleDateString(), bookedClass: selectedCoach, bookedFare: coachData.fare, bookedStatus: coachData.status };
                      setActiveJourneys(prev => [...prev, ticketRecord]);
                      setLiveTrains(prev => prev.filter(t => t.Train_Number !== selectedTrain.Train_Number));
                      addLog(`Locked ${selectedCoach} for ${selectedTrain.Train_Name}. Initializing pre-routing safety scan.`, 'success');
                      
                      const journeyType = selectedTrain.is_flight ? 'Flight' : 'Train';
                      const bookableFare = `at ₹${coachData.fare} (${selectedCoach} - ${coachData.status})`;
                      const autoQuery = `I have locked the ${journeyType}: ${selectedTrain.Train_Name} (${selectedTrain.Train_Number}) from ${selectedTrain.Source} to ${selectedTrain.Destination} ${bookableFare}. Please give me a quick price & delay analysis, and ask if I should check the weather!`;
                      setSelectedTrain(null);
                      setActiveTab('active');
                      setTimeout(() => { handleSend(null, autoQuery); }, 500);
                    }}
                    disabled={!canBook}
                    className={`w-full py-3 text-white font-bold rounded-xl transition-all shadow-lg ${!canBook ? 'bg-slate-400 dark:bg-slate-800 text-slate-300 cursor-not-allowed opacity-70 shadow-none' : selectedTrain.is_flight ? 'bg-indigo-500 hover:bg-indigo-600 hover:scale-[1.01] active:scale-[0.99] shadow-indigo-500/20' : 'bg-secondary hover:bg-blue-600 hover:scale-[1.01] active:scale-[0.99] shadow-blue-500/20'}`}
                  >
                    {isCompletelyUnavailable ? 'Booking Unavailable' : selectedCoach ? `Lock ${selectedCoach} & Add to Vault` : 'Select a Class to Proceed'}
                  </button>
                );
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ==========================================
// COMPONENT 2: THE SECURE CHECKOUT PAGE (TRAINS/FLIGHTS)
// ==========================================
function CheckoutPage() {
  const { draftId } = useParams();
  const [draftData, setDraftData] = useState(null);
  const [activeTrain, setActiveTrain] = useState(null);
  const [passengers, setPassengers] = useState([{name: "", age: "", gender: "Male"}]); // 🚨 UPDATE 1: Added Gender Default
  const [coach, setCoach] = useState('');
  
  const [step, setStep] = useState(1); 
  const [isProcessing, setIsProcessing] = useState(false);
  const [pnr, setPnr] = useState('');

  useEffect(() => {
    const savedDraft = JSON.parse(localStorage.getItem('nexusDraftData') || '{}');
    const savedTrain = JSON.parse(localStorage.getItem('nexusActiveTrain') || '{}');
    if (savedTrain && savedTrain.Train_Name) {
      setActiveTrain(savedTrain);
      // 🚨 NAYA SAFE PARSING LOGIC
      try { 
          let rawPassengers = savedDraft.passengers || '[]';
          
          // Agar LLM ne single quotes ('') bheje hain, toh usko double quotes ("") mein badlo
          if (typeof rawPassengers === 'string') {
              rawPassengers = rawPassengers.replace(/'/g, '"');
          }
          
          const parsed = typeof rawPassengers === 'string' ? JSON.parse(rawPassengers) : rawPassengers;
          
          if (parsed && parsed.length > 0) {
             setPassengers(parsed.map(p => ({ 
                 name: p.name || "", 
                 age: p.age || "", 
                 gender: p.gender || "Male" 
             })));
          } else {
             setPassengers([{name: "Primary User", age: 21, gender: "Male"}]);
          }
      } catch (e) { 
          console.error("Draft parsing failed, falling back to default:", e);
          setPassengers([{name: "Primary User", age: 21, gender: "Male"}]); 
      }
      setCoach(savedTrain.bookedClass || '');
    }
  }, [draftId]);

  if (!activeTrain) return <div className="h-screen bg-slate-900 flex items-center justify-center text-white font-bold">Loading / Invalid Link</div>;

  const coachData = activeTrain.Availability_and_Fares[coach] || {};
  const baseFare = parseInt(coachData?.fare?.toString().replace(/[^0-9]/g, '') || 0); // 🚨 SAFE STRING CAST
  
  const hasInvalidPassengers = passengers.some(p => !p.name.trim() || !p.age);
  const validPassengerCount = passengers.filter(p => p.name.trim() && p.age).length;
  const totalAmount = validPassengerCount === 0 ? 0 : (baseFare * validPassengerCount) + 50; 

  const processPayment = () => {
    setIsProcessing(true);
    const validPax = passengers.filter(p => p.name.trim() !== '');
    
    // Save passengers globally for Hotel prefill
    localStorage.setItem('nexusLastPassengers', JSON.stringify(validPax));
    
    setTimeout(() => {
       const isFlight = activeTrain.is_flight || false;
       
       let finalPnr = "";
       if (isFlight) {
           const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
           for (let i = 0; i < 6; i++) {
               finalPnr += chars.charAt(Math.floor(Math.random() * chars.length));
           }
       } else {
           finalPnr = Math.floor(1000000000 + Math.random() * 9000000000).toString();
       }
       
       setPnr(finalPnr);
       setStep(3);
       setIsProcessing(false);

       // 🚨 UPDATE 3: Added total_amount and is_solo into payload so listener can send it to DB
       const payload = {
           pnr: finalPnr,
           trainName: activeTrain.Train_Name,
           source: activeTrain.Source,
           dest: activeTrain.Destination,
           dep: activeTrain.Departure,
           arr: activeTrain.Arrival,
           passengers: validPax, 
           bookedClass: coach,
           bookedStatus: coachData.status,
           isFlight: isFlight,
           total_amount: totalAmount, // For accurate DB entry
           is_solo: validPax.length === 1 // For accurate DB entry
       };
       localStorage.setItem('nexusPaymentSuccess', JSON.stringify(payload));
       
    }, 2500);
  };

  return (
    <div className="min-h-screen bg-[#0B1120] flex items-center justify-center p-4 py-12">
      <div className="bg-[#111827] w-full max-w-2xl rounded-3xl shadow-2xl border border-slate-800 overflow-hidden text-white">
        
        {/* STEP 1: REVIEW PAGE */}
        {step === 1 && (
          <div className="p-8">
            <h2 className="text-2xl font-black mb-6 border-b border-slate-800 pb-4 text-white">Review Booking</h2>
            
            <div className="bg-slate-900/50 p-6 rounded-2xl mb-8 border border-slate-800">
               <p className="text-xl font-black tracking-wide mb-4">{activeTrain.Train_Name} <span className="text-sm font-bold text-slate-500">({activeTrain.Train_Number})</span></p>
               
               <div className="flex justify-between items-center mb-6 border-b border-slate-800 pb-6">
                  <div className="text-left"><p className="text-3xl font-black">{activeTrain.Departure}</p><p className="text-sm font-bold text-slate-400 mt-1">{activeTrain.Source}</p></div>
                  <div className="text-xs font-bold text-slate-500 border-t border-dashed border-slate-700 w-32 text-center pt-2">{activeTrain.Travel_Time}</div>
                  <div className="text-right"><p className="text-3xl font-black">{activeTrain.Arrival}</p><p className="text-sm font-bold text-slate-400 mt-1">{activeTrain.Destination}</p></div>
               </div>

               <p className="text-xs font-bold text-slate-500 uppercase mb-3">Change Coach</p>
               <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {Object.entries(activeTrain.Availability_and_Fares).map(([c, data]) => {
                     const s = data.status ? String(data.status).toLowerCase() : 'n/a';
                     const isUnavailable = s.includes('regret') || s.includes('not avail') || s.includes('cancel') || s === 'n/a';
                     const isSelected = coach === c;
                     return (
                        <div 
                          key={c} 
                          onClick={() => !isUnavailable && setCoach(c)} 
                          className={`p-3 rounded-xl border flex flex-col items-center justify-center transition-all ${isUnavailable ? 'opacity-40 cursor-not-allowed border-slate-800 bg-slate-900' : isSelected ? 'border-blue-500 bg-blue-500/10 ring-1 ring-blue-500 cursor-pointer' : 'border-slate-700 bg-slate-800 cursor-pointer hover:border-slate-500'}`}
                        >
                           <span className="font-black text-lg">{c}</span>
                           <span className="font-bold text-sm">₹{data.fare}</span>
                           <span className={`mt-2 text-[10px] uppercase font-black tracking-wider px-2 py-0.5 rounded border ${getStatusBadgeStyle(data.status)}`}>{data.status}</span>
                        </div>
                     )
                  })}
               </div>
            </div>

            <div className="mb-8">
               <div className="flex justify-between items-center mb-4">
                 <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Passenger Manifest</p>
                 <button onClick={() => setPassengers([...passengers, {name: "", age: "", gender: "Male"}])} className="text-xs font-bold bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-lg transition-all">+ Add Passenger</button>
               </div>
               
               <div className="space-y-3">
                 {passengers.map((p, i) => (
                    <div key={i} className="flex gap-3">
                       <input 
                         type="text" 
                         value={p.name} 
                         placeholder="Passenger Name" 
                         onChange={(e) => {const n=[...passengers]; n[i].name=e.target.value; setPassengers(n)}} 
                         className="flex-1 bg-slate-900 border border-slate-700 p-4 rounded-xl outline-none focus:border-blue-500 font-bold" 
                       />
                       <input 
                         type="number" 
                         value={p.age} 
                         placeholder="Age" 
                         onChange={(e) => {const n=[...passengers]; n[i].age=e.target.value; setPassengers(n)}} 
                         className="w-20 bg-slate-900 border border-slate-700 p-4 rounded-xl outline-none focus:border-blue-500 font-bold text-center" 
                       />
                       
                       {/* 🚨 UPDATE 4: Gender Selector UI */}
                       <select 
                         value={p.gender || "Male"} 
                         onChange={(e) => {const n=[...passengers]; n[i].gender=e.target.value; setPassengers(n)}}
                         className="w-28 bg-slate-900 border border-slate-700 p-4 rounded-xl outline-none focus:border-blue-500 font-bold text-white transition-all appearance-none"
                       >
                         <option value="Male">Male</option>
                         <option value="Female">Female</option>
                         <option value="Other">Other</option>
                       </select>

                       {passengers.length > 1 && (
                          <button onClick={() => setPassengers(passengers.filter((_, idx) => idx !== i))} className="px-4 text-red-500 bg-slate-900 hover:bg-red-500/20 border border-slate-700 rounded-xl transition-all"><Trash2 size={20} /></button>
                       )}
                    </div>
                 ))}
               </div>
            </div>

            <div className="border-t border-slate-800 pt-6 flex justify-between items-center">
               <div>
                   <p className="text-sm font-bold text-slate-500">Total Payable Fare</p>
                   <p className="text-3xl font-black text-emerald-400 mt-1">₹{totalAmount}</p>
               </div>
               <button 
                  onClick={() => {
                    if (passengers.length === 0 || validPassengerCount === 0) return alert("Please add at least 1 valid passenger!");
                    if (hasInvalidPassengers) return alert("Please fill all names and ages, or remove the empty rows by clicking the Red trash bin.");
                    setStep(2);
                  }} 
                  className="bg-blue-600 hover:bg-blue-500 px-10 py-4 rounded-xl font-black text-lg transition-all shadow-lg shadow-blue-600/30 tracking-wide"
               >
                 Proceed
               </button>
            </div>
          </div>
        )}

        {/* STEP 2: PAYMENT QR PAGE */}
        {step === 2 && (
          <div className="p-12 text-center animate-in slide-in-from-right duration-300">
             <h2 className="text-3xl font-black mb-2">Complete Payment</h2>
             <p className="text-slate-400 mb-10 font-bold">Scan the QR code below via any UPI App</p>
             
             <div className="bg-white p-5 rounded-3xl inline-block mb-10 shadow-2xl">
                <img src={`https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=pay_nexus_${totalAmount}`} alt="UPI QR Code" className="w-56 h-56" />
             </div>
             
             <p className="text-2xl font-black text-emerald-400 mb-8">Amount to Pay: ₹{totalAmount}</p>

             <div className="flex gap-4">
                 <button onClick={() => setStep(1)} className="flex-1 py-4 bg-slate-800 rounded-xl font-bold">Go Back</button>
                 {!isProcessing ? (
                   <button onClick={processPayment} className="flex-1 py-4 bg-emerald-500 hover:bg-emerald-600 font-black rounded-xl flex items-center justify-center gap-2">Simulate Payment</button>
                 ) : (
                   <button disabled className="flex-1 py-4 bg-emerald-600 font-black rounded-xl flex items-center justify-center gap-3 opacity-80"><Loader2 className="animate-spin" size={20}/> Processing Securely...</button>
                 )}
             </div>
          </div>
        )}

        {/* STEP 3: SUCCESS PAGE */}
        {step === 3 && (
          <div className="text-center py-20 animate-in zoom-in duration-500">
             <div className="w-24 h-24 bg-emerald-500 rounded-full flex items-center justify-center mx-auto mb-8 shadow-[0_0_30px_rgba(16,185,129,0.5)]"><CheckCircle2 size={48} className="text-white" /></div>
             <h2 className="text-4xl font-black mb-3">Booking Confirmed!</h2>
             <p className="text-slate-400 mb-10 font-bold text-lg">Your detailed e-ticket has been dispatched.</p>
             <div className="bg-slate-900 border border-slate-800 p-8 rounded-2xl mx-12 mb-12">
                <p className="text-sm text-slate-500 uppercase font-black tracking-widest mb-3">Your PNR Number</p>
                <p className="text-5xl font-mono font-black text-blue-400 tracking-wider">{pnr}</p>
             </div>
             <button onClick={() => window.close()} className="py-4 px-12 bg-slate-800 hover:bg-slate-700 rounded-xl font-black transition-all">Close Tab</button>
          </div>
        )}
      </div>
    </div>
  );
}

// ==========================================
// COMPONENT 3: NEW SECURE CHECKOUT PAGE (HOTELS)
// ==========================================
// ==========================================
// COMPONENT 3: NEW SECURE CHECKOUT PAGE (HOTELS)
// ==========================================
function HotelCheckoutPage() {
  const { draftId } = useParams();
  const [draftData, setDraftData] = useState(null);
  const [passengers, setPassengers] = useState([]);
  const [rooms, setRooms] = useState(1); 
  const [days, setDays] = useState(1); // 🚨 NEW STATE: Days of Stay
  const [step, setStep] = useState(1); 
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    const savedDraft = JSON.parse(localStorage.getItem('nexusHotelDraftData') || '{}');
    
    if (savedDraft && savedDraft.hotel_name) {
      setDraftData(savedDraft);
      
      // 🚨 AUTO-PREFILL LOGIC (Fixed)
      const lastPax = JSON.parse(localStorage.getItem('nexusLastPassengers') || 'null');
      if (lastPax && lastPax.length > 0) {
          setPassengers(lastPax);
          setRooms(Math.max(1, Math.ceil(lastPax.length / 2))); // Auto-calculate rooms needed
      } else {
          setPassengers([{name: "Yogesh", age: 21}]);
      }
    }
  }, [draftId]);

  if (!draftData) return <div className="h-screen bg-slate-900 flex items-center justify-center text-white font-bold">Loading Secure Draft...</div>;

  // 🚨 DYNAMIC PRICING LOGIC
  const baseFare = parseInt(draftData.price) || 0;
  const taxes = rooms * days * 150; 
  const totalAmount = (baseFare * rooms * days) + taxes; 

  const processPayment = async () => {
    setIsProcessing(true);
    
    try {
        const response = await fetch('http://localhost:8000/api/accommodations/book', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              pnr: draftData.pnr || "CAB9998887",
              option_id: "HTL-BOOKED",
              option_name: `${draftData.hotel_name} (${draftData.room_type} | ${days} Nights)`,
              price: totalAmount, // The dynamically calculated total will go to DB
              passengers: passengers.filter(p => p.name.trim() !== '')
            })
        });
        
        const resData = await response.json();
        
        if (resData.status === 'success') {
            localStorage.setItem('nexusHotelPaymentSuccess', JSON.stringify({
               hotel_name: draftData.hotel_name,
               room_no: resData.room_no,
               stay_booking_id: resData.stay_booking_id,
               // 🚨 DYNAMIC FIX: Backend ka bheja hua proper PNR use karo!
               pnr: resData.pnr 
            }));
            setStep(3);
        } else {
            throw new Error("Backend Returned Error");
        }
    } catch (e) {
        console.error("Booking API Failed, running simulation fallback.", e);
        const fakeRoom = "10" + Math.floor(Math.random() * 9);
        localStorage.setItem('nexusHotelPaymentSuccess', JSON.stringify({
               hotel_name: draftData.hotel_name,
               room_no: fakeRoom,
               stay_booking_id: `STAY-SIM-${Math.floor(Math.random() * 999)}`,
               pnr: draftData.pnr || "CAB9998887"
        }));
        setStep(3);
    } finally {
        setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B1120] flex items-center justify-center p-4 py-12 font-sans">
      <div className="bg-[#111827] w-full max-w-2xl rounded-3xl shadow-2xl border border-slate-800 overflow-hidden text-white">
        
        {step === 1 && (
          <div className="p-8 animate-in fade-in">
            <h2 className="text-2xl font-black mb-6 border-b border-slate-800 pb-4 text-white flex items-center gap-3">
               <Hotel /> Secure Stay Checkout
            </h2>
            
            {/* HOTEL & ROOM SUMMARY */}
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl mb-6 flex justify-between items-center">
               <div>
                  <p className="text-xl font-black tracking-wide text-white">{draftData.hotel_name}</p>
                  <p className="text-sm font-bold text-blue-400 mt-1">{draftData.room_type || 'Premium Deluxe'}</p>
               </div>
               <div className="text-right">
                  <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Base Tariff / Night</p>
                  <p className="text-2xl font-black text-slate-200">₹{baseFare}</p>
               </div>
            </div>

            {/* 🚨 UPDATED: DYNAMIC ROOM & DAYS SELECTOR */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
               {/* Rooms */}
               <div className="flex justify-between items-center bg-slate-800/50 p-5 rounded-2xl border border-slate-700/50">
                  <div>
                     <span className="font-bold text-slate-200 block">Rooms</span>
                     <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wide">Max 2 Pax/Room</span>
                  </div>
                  <div className="flex items-center gap-3 bg-slate-900 p-1.5 rounded-xl border border-slate-800">
                     <button onClick={() => setRooms(Math.max(1, rooms - 1))} className="bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg font-black text-slate-300 transition-all">-</button>
                     <span className="text-lg font-black w-6 text-center">{rooms}</span>
                     <button onClick={() => setRooms(rooms + 1)} className="bg-blue-600 hover:bg-blue-500 px-3 py-1.5 rounded-lg font-black transition-all">+</button>
                  </div>
               </div>

               {/* Days */}
               <div className="flex justify-between items-center bg-slate-800/50 p-5 rounded-2xl border border-slate-700/50">
                  <div>
                     <span className="font-bold text-slate-200 block">Duration</span>
                     <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wide">Total Nights</span>
                  </div>
                  <div className="flex items-center gap-3 bg-slate-900 p-1.5 rounded-xl border border-slate-800">
                     <button onClick={() => setDays(Math.max(1, days - 1))} className="bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg font-black text-slate-300 transition-all">-</button>
                     <span className="text-lg font-black w-6 text-center">{days}</span>
                     <button onClick={() => setDays(days + 1)} className="bg-blue-600 hover:bg-blue-500 px-3 py-1.5 rounded-lg font-black transition-all">+</button>
                  </div>
               </div>
            </div>

            {/* GUEST ROSTER */}
            <div className="mb-8">
               <div className="flex justify-between items-center mb-4">
                 <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Guest Roster</p>
                 <button onClick={() => setPassengers([...passengers, {name: "", age: ""}])} className="text-xs font-bold bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-lg transition-all border border-slate-700">+ Add Guest</button>
               </div>
               <div className="space-y-3">
                 {passengers.map((p, i) => (
                    <div key={i} className="flex gap-3">
                       <input 
                          type="text" 
                          value={p.name} 
                          placeholder="Guest Name" 
                          onChange={(e) => {const n=[...passengers]; n[i].name=e.target.value; setPassengers(n)}} 
                          className="flex-1 bg-slate-950 border border-slate-800 p-4 rounded-xl outline-none focus:border-blue-500 font-bold text-white transition-all" 
                       />
                       <input 
                          type="number" 
                          value={p.age} 
                          placeholder="Age" 
                          onChange={(e) => {const n=[...passengers]; n[i].age=e.target.value; setPassengers(n)}} 
                          className="w-24 bg-slate-950 border border-slate-800 p-4 rounded-xl outline-none focus:border-blue-500 font-bold text-center text-white transition-all" 
                       />
                       {passengers.length > 1 && (
                          <button onClick={() => setPassengers(passengers.filter((_, idx) => idx !== i))} className="px-4 text-red-500 bg-slate-950 hover:bg-red-500/20 border border-slate-800 rounded-xl transition-all">
                             <Trash2 size={20} />
                          </button>
                       )}
                    </div>
                 ))}
               </div>
            </div>

            {/* TOTAL PAYLOAD */}
            <div className="bg-slate-800/30 p-6 -mx-8 -mb-8 flex justify-between items-center border-t border-slate-800">
               <div>
                   <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Total Payload ({rooms} Rooms, {days} Nights)</p>
                   <p className="text-3xl font-black text-emerald-400">₹{totalAmount}</p>
                   <p className="text-[10px] text-slate-500 mt-1 font-bold">Includes ₹{taxes} taxes & fees</p>
               </div>
               <button 
                  onClick={() => {
                    if (passengers.filter(p => p.name.trim() !== '').length === 0) return alert("Please add at least 1 guest!");
                    setStep(2);
                  }} 
                  className="bg-blue-600 hover:bg-blue-500 px-10 py-4 rounded-xl font-black text-lg transition-all shadow-lg shadow-blue-600/30 tracking-wide"
               >
                 Review & Pay
               </button>
            </div>
          </div>
        )}

        {/* STEP 2: PAYMENT QR SIMULATION */}
        {step === 2 && (
          <div className="p-12 text-center animate-in slide-in-from-right duration-300">
             <h2 className="text-3xl font-black mb-2">Complete Payment</h2>
             <p className="text-slate-400 mb-10 font-bold">Scan QR code to lock your stay at {draftData.hotel_name}</p>
             
             <div className="bg-white p-5 rounded-3xl inline-block mb-10 shadow-2xl">
                <img src={`https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=pay_nexus_hotel_${totalAmount}`} alt="UPI QR Code" className="w-56 h-56" />
             </div>
             
             <p className="text-2xl font-black text-emerald-400 mb-8">Amount to Pay: ₹{totalAmount}</p>

             <div className="flex gap-4">
                 <button onClick={() => setStep(1)} className="flex-1 py-4 bg-slate-800 rounded-xl font-bold transition-all hover:bg-slate-700">Go Back</button>
                 <button onClick={processPayment} disabled={isProcessing} className={`flex-1 py-4 font-black rounded-xl flex items-center justify-center gap-2 transition-all ${isProcessing ? 'bg-emerald-600 opacity-80' : 'bg-emerald-500 hover:bg-emerald-400 shadow-lg shadow-emerald-500/20'}`}>
                    {isProcessing ? <><Loader2 className="animate-spin" size={20}/> Processing...</> : 'Simulate Payment'}
                 </button>
             </div>
          </div>
        )}

        {/* STEP 3: SUCCESS SCREEN */}
        {step === 3 && (
          <div className="text-center py-20 animate-in zoom-in duration-500">
             <div className="w-24 h-24 bg-emerald-500 rounded-full flex items-center justify-center mx-auto mb-8 shadow-[0_0_30px_rgba(16,185,129,0.5)]">
                 <CheckCircle2 size={48} className="text-white" />
             </div>
             <h2 className="text-4xl font-black mb-3">Stay Secured!</h2>
             <p className="text-slate-400 mb-10 font-bold text-lg">Your booking details have been synced to Agentra.</p>
             <button onClick={() => window.close()} className="py-4 px-12 bg-slate-800 hover:bg-slate-700 rounded-xl font-black transition-all">Close Tab</button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [isDarkMode, setIsDarkMode] = useState(true);
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ChatInterface />} />
        <Route path="/checkout/:draftId" element={<CheckoutPage />} />
        <Route path="/hotel-checkout/:draftId" element={<HotelCheckoutPage />} />
      </Routes>
    </Router>
  );
}