import React from 'react';
import { Header } from './Header';
import { Footer } from './Footer';
import { BottomNavigation } from './MobileNavigation';
import { useLocation } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  const navigation = [
    { name: 'Games', href: '/games', icon: '🎮', current: location.pathname.startsWith('/games') },
    { name: 'Statistics', href: '/statistics', icon: '📊', current: location.pathname.startsWith('/statistics') },
    { name: 'Leaderboard', href: '/leaderboard', icon: '🏆', current: location.pathname.startsWith('/leaderboard') },
  ];

  return (
    <div className="layout">
      <Header />
      <main className="main-content">
        {children}
      </main>
      <Footer />
      <BottomNavigation navigation={navigation} />

      <style jsx>{`
        .layout {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          background-color: #f9fafb;
        }

        .main-content {
          flex: 1;
          padding: 0;
          max-width: 1200px;
          width: 100%;
          margin: 0 auto;
          padding-bottom: 2rem;
        }

        @media (min-width: 640px) {
          .main-content {
            padding: 0 1rem 2rem 1rem;
          }
        }

        @media (min-width: 768px) {
          .main-content {
            padding-bottom: 2rem;
          }
        }

        @media (min-width: 1024px) {
          .main-content {
            padding: 0 2rem 2rem 2rem;
          }
        }
      `}</style>
    </div>
  );
};