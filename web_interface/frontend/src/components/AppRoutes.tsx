import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Dashboard } from '../pages/Dashboard';
import { Games } from '../pages/Games';
import { Statistics } from '../pages/Statistics';
import { Leaderboard } from '../pages/Leaderboard';
import { GameDetailView } from './GameDetailView';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Dashboard / Home */}
      <Route path="/" element={<Dashboard />} />
      
      {/* Games Section */}
      <Route path="/games" element={<Games />} />
      <Route path="/games/:gameId" element={<GameDetailView />} />
      
      {/* Statistics Section */}
      <Route path="/statistics" element={<Statistics />} />
      
      {/* Leaderboard Section */}
      <Route path="/leaderboard" element={<Leaderboard />} />
      <Route path="/players/:playerId" element={<div>Player Detail (Coming Soon)</div>} />
      
      {/* Catch-all route - redirect to home */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};