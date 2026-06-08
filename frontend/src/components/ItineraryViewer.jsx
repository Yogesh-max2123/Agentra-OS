import React, { useEffect, useState } from 'react';
import { MapPin, Clock, Ticket, ExternalLink, Star } from 'lucide-react';
import './ItineraryViewer.css';


const PlaceCard = ({ place }) => {
    const [imageUrl, setImageUrl] = useState('');
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchImage = async () => {
            try {
                const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                const apiKey = import.meta.env.VITE_PEXELS_API_KEY;
                const searchQuery = encodeURIComponent(`${place.name} ${place.map_query.split(',')[0]}`);
                
                const response = await fetch(`https://api.pexels.com/v1/search?query=${searchQuery}&per_page=1`, {
                    headers: { Authorization: apiKey }
                });
                
                const data = await response.json();
                if (data.photos && data.photos.length > 0) {
                    setImageUrl(data.photos[0].src.large);
                } else {
                    
                    setImageUrl(`https://loremflickr.com/800/600/${encodeURIComponent(place.name.split(' ')[0])},landmark/all`);
                }
            } catch (err) {
                setImageUrl(`https://loremflickr.com/800/600/${encodeURIComponent(place.name.split(' ')[0])},landmark/all`);
            } finally {
                setIsLoading(false);
            }
        };
        fetchImage();
    }, [place]);

    const handleMapsRedirect = (mapQuery) => {
        window.open(`https://maps.google.com/?q=${encodeURIComponent(mapQuery)}`, '_blank');
    };

    return (
        <div className="place-card" onClick={() => handleMapsRedirect(place.map_query)}>
            <div className={`place-image-wrapper ${isLoading ? 'loading-shimmer' : ''}`}>
                <div 
                    className="place-image" 
                    style={{ backgroundImage: `url('${imageUrl}')` }}
                />
                <div className="rating-badge"><Star size={12} className="fill-yellow-400 text-yellow-400" /> {place.rating}</div>
            </div>
            
            <div className="place-content">
                <div>
                    <h4 className="place-name">{place.name}</h4>
                    <p className="place-address"><MapPin size={12} className="shrink-0" /> {place.address}</p>
                </div>
                
                <div className="place-meta">
                    <span className="timing"><Clock size={12} className="text-blue-500" /> {place.timing}</span>
                    <span className="price"><Ticket size={12} className="text-emerald-500" /> {place.ticket_pricing}</span>
                </div>
                
                <p className="place-desc">{place.description}</p>
                
                <button className="maps-btn">
                    View on Google Maps <ExternalLink size={14} />
                </button>
            </div>
        </div>
    );
};

const ItineraryViewer = ({ pnr }) => {
    const [itinerary, setItinerary] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchItinerary = async () => {
            try {
                const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                const response = await fetch(`${API_BASE}/api/trips/${pnr}/itinerary`);
                const result = await response.json();
                if (result.status === 'success') {
                    setItinerary(result.data.itinerary);
                }
            } catch (error) {
                console.error("Failed to fetch itinerary", error);
            } finally {
                setLoading(false);
            }
        };
        if (pnr) fetchItinerary();
    }, [pnr]);

    if (loading) return <div className="itinerary-loader"><div className="spinner"></div><p>Agentra is structuring your plan...</p></div>;
    if (!itinerary) return <div className="itinerary-empty">No itinerary planned yet.</div>;

    return (
        <div className="itinerary-container">
            <h2 className="itinerary-title">Your Custom Trip Plan</h2>
            
            {itinerary.map((dayPlan, idx) => (
                <div key={idx} className="day-section">
                    <div className="day-header-block">
                        <h3 className="day-header">{dayPlan.day}</h3>
                        <p className="day-theme">Theme: {dayPlan.theme}</p>
                    </div>
                    
                    <div className="places-grid">
                        {dayPlan.places.map((place, pIdx) => (
                            <PlaceCard key={pIdx} place={place} />
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
};

export default ItineraryViewer;