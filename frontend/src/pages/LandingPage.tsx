import { Link } from 'react-router-dom'
import { ArrowRight, BookOpen, Brain, TrendingUp } from 'lucide-react'

const LandingPage = () => {
  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#0B0F1A' }}>
      {/* Header */}
      <header style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px 16px', borderBottom: '1px solid #1E2940' }}>
        <nav style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#60A5FA' }}>
            Know-It-All Tutor
          </div>
          <Link
            to="/auth"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: '#60A5FA',
              color: '#0B0F1A',
              padding: '8px 16px',
              borderRadius: '6px',
              textDecoration: 'none',
              fontWeight: '600',
            }}
          >
            Get Started
          </Link>
        </nav>
      </header>

      {/* Hero Section */}
      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '80px 16px' }}>
        <div style={{ textAlign: 'center', maxWidth: '896px', margin: '0 auto' }}>
          <h1 style={{ fontSize: '48px', fontWeight: 'bold', color: '#F8FAFC', marginBottom: '24px', lineHeight: '1.1' }}>
            Master Complex Terminology with
            <span style={{ color: '#60A5FA' }}> AI-Powered Learning</span>
          </h1>

          <p style={{ fontSize: '20px', color: '#94A3B8', marginBottom: '32px', lineHeight: '1.6' }}>
            Transform terminology-heavy subjects into interactive, hands-on tutorials.
            Perfect for AWS certification, Python programming, and more.
          </p>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Link
              to="/auth"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#60A5FA',
                color: '#0B0F1A',
                padding: '12px 24px',
                borderRadius: '6px',
                textDecoration: 'none',
                fontWeight: '600',
                fontSize: '16px',
              }}
            >
              Start Learning
              <ArrowRight size={20} style={{ marginLeft: '8px', color: '#0B0F1A' }} />
            </Link>
          </div>
        </div>

        {/* Features */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '32px', marginTop: '80px' }}>
          <div style={{ backgroundColor: '#111827', padding: '24px', borderRadius: '8px', border: '1px solid #1E2940', boxShadow: '0 2px 8px rgba(0,0,0,0.4)', textAlign: 'center' }}>
            <div style={{ width: '48px', height: '48px', backgroundColor: '#1E3A5F', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <BookOpen size={24} style={{ color: '#60A5FA' }} />
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#F8FAFC' }}>Domain-Agnostic Learning</h3>
            <p style={{ color: '#94A3B8', lineHeight: '1.5' }}>
              Create custom knowledge domains for any subject. From AWS to Python,
              the platform adapts to your learning needs.
            </p>
          </div>

          <div style={{ backgroundColor: '#111827', padding: '24px', borderRadius: '8px', border: '1px solid #1E2940', boxShadow: '0 2px 8px rgba(0,0,0,0.4)', textAlign: 'center' }}>
            <div style={{ width: '48px', height: '48px', backgroundColor: '#1E3A5F', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <Brain size={24} style={{ color: '#60A5FA' }} />
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#F8FAFC' }}>Intelligent Evaluation</h3>
            <p style={{ color: '#94A3B8', lineHeight: '1.5' }}>
              AI-powered semantic answer evaluation provides fair, accurate feedback
              on your understanding of complex terminology.
            </p>
          </div>

          <div style={{ backgroundColor: '#111827', padding: '24px', borderRadius: '8px', border: '1px solid #1E2940', boxShadow: '0 2px 8px rgba(0,0,0,0.4)', textAlign: 'center' }}>
            <div style={{ width: '48px', height: '48px', backgroundColor: '#1E3A5F', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <TrendingUp size={24} style={{ color: '#60A5FA' }} />
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#F8FAFC' }}>Progress Tracking</h3>
            <p style={{ color: '#94A3B8', lineHeight: '1.5' }}>
              Monitor your mastery level with detailed progress analytics and
              personalized learning recommendations.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}

export default LandingPage
