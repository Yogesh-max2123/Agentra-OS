import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react';
import LandingPage from './components/LandingPage';
import ChatInterface, { CheckoutPage, HotelCheckoutPage } from './components/Dashboard';

export default function App() {
  const [isDarkMode, setIsDarkMode] = useState(true);

  return (
    <Router>
      <Routes>
        {/* Public Route */}
        <Route path="/" element={<LandingPage />} />
        
        {/* Protected Dashboard Route */}
        <Route path="/dashboard" element={
          <>
            <SignedIn>
              {/* Sirf tab dikhega jab login hoga */}
              <ChatInterface isDarkMode={isDarkMode} setIsDarkMode={setIsDarkMode} />
            </SignedIn>
            <SignedOut>
              {/* Login nahi hai toh seedha Clerk ke secure login page par bhej do */}
              <RedirectToSignIn />
            </SignedOut>
          </>
        } />

        {/* Protected Checkout Routes */}
        <Route path="/checkout/:draftId" element={
          <><SignedIn><CheckoutPage isDarkMode={isDarkMode} /></SignedIn><SignedOut><RedirectToSignIn /></SignedOut></>
        } />
        <Route path="/hotel-checkout/:draftId" element={
          <><SignedIn><HotelCheckoutPage isDarkMode={isDarkMode} /></SignedIn><SignedOut><RedirectToSignIn /></SignedOut></>
        } />
      </Routes>
    </Router>
  );
}