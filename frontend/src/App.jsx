import React from 'react'
import { Routes, Route, NavLink, Navigate } from 'react-router-dom'
import ProjectsPage from './pages/ProjectsPage.jsx'
import ProjectPage from './pages/ProjectPage.jsx'

export default function App() {
  return (
    <div className="layout">
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/projects" className="brand">
            Кредитный анализ
          </NavLink>
          <nav className="menu">
            <NavLink to="/projects" className={({ isActive }) => 'menu-link' + (isActive ? ' active' : '')}>
              Реестр проектов
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:id/*" element={<ProjectPage />} />
          <Route path="*" element={<div className="card">Страница не найдена</div>} />
        </Routes>
      </main>
    </div>
  )
}
