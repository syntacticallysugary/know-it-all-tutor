import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { apiClient, QuizSession, QuizQuestion, AnswerResult, QuizSummary } from '../services/api'
import QuizQuestionCard from '../components/Quiz/QuizQuestionCard'
import QuizProgress from '../components/Quiz/QuizProgress'
import QuizSummaryCard from '../components/Quiz/QuizSummaryCard'
import LoadingSpinner from '../components/UI/LoadingSpinner'

interface QuizState {
  session: QuizSession | null
  currentQuestion: QuizQuestion | null
  nextQuestion: QuizQuestion | null
  quizMode: 'forward' | 'reverse'
  isLoading: boolean
  error: string | null
  isSubmitting: boolean
  lastResult: AnswerResult | null
  summary: QuizSummary | null
  showingSummary: boolean
  isPaused: boolean
}

const QuizInterface = () => {
  const { domainId } = useParams<{ domainId: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const modeParam = (searchParams.get('mode') as 'forward' | 'reverse') || 'forward'

  const [state, setState] = useState<QuizState>({
    session: null,
    currentQuestion: null,
    nextQuestion: null,
    quizMode: modeParam,
    isLoading: true,
    error: null,
    isSubmitting: false,
    lastResult: null,
    summary: null,
    showingSummary: false,
    isPaused: false
  })

  // Initialize quiz session
  useEffect(() => {
    if (!domainId) {
      navigate('/app/domains')
      return
    }

    initializeQuiz()
  }, [domainId])

  const initializeQuiz = async () => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }))

      const session = await apiClient.startQuiz(domainId!, modeParam)

      setState(prev => ({
        ...prev,
        session,
        currentQuestion: session.current_question || null,
        quizMode: session.quiz_mode || modeParam,
        isLoading: false,
        isPaused: session.status === 'paused'
      }))
    } catch (error) {
      console.error('Failed to start quiz:', error)
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to start quiz',
        isLoading: false
      }))
    }
  }

  const handleAnswerSubmit = async (answer: string) => {
    if (!state.session || !state.currentQuestion) return

    try {
      setState(prev => ({ ...prev, isSubmitting: true, error: null }))
      
      const result = await apiClient.submitAnswer({
        session_id: state.session.session_id,
        answer: answer.trim()
      })

      setState(prev => ({
        ...prev,
        lastResult: result,
        isSubmitting: false,
        // currentQuestion stays as the question just answered so the result
        // display shows the right context. nextQuestion is staged and only
        // moves to currentQuestion when the user dismisses the result.
        nextQuestion: result.quiz_completed ? null : (result.next_question || null),
        session: prev.session ? {
          ...prev.session,
          progress: result.progress
        } : null
      }))

      // If quiz is completed, fetch summary
      if (result.quiz_completed) {
        await fetchQuizSummary(state.session.session_id)
      }
    } catch (error) {
      console.error('Failed to submit answer:', error)
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to submit answer',
        isSubmitting: false
      }))
    }
  }

  const fetchQuizSummary = async (sessionId: string) => {
    try {
      const summary = await apiClient.getQuizSummary(sessionId)
      setState(prev => ({ ...prev, summary }))
    } catch (error) {
      console.error('Failed to fetch quiz summary:', error)
    }
  }

  const handlePauseQuiz = async () => {
    if (!state.session) return

    try {
      await apiClient.pauseQuiz(state.session.session_id)
      setState(prev => ({ ...prev, isPaused: true }))
    } catch (error) {
      console.error('Failed to pause quiz:', error)
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to pause quiz'
      }))
    }
  }

  const handleResumeQuiz = async () => {
    if (!state.session) return

    try {
      const session = await apiClient.resumeQuiz(state.session.session_id)
      setState(prev => ({
        ...prev,
        session,
        currentQuestion: session.current_question || null,
        isPaused: false
      }))
    } catch (error) {
      console.error('Failed to resume quiz:', error)
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to resume quiz'
      }))
    }
  }

  const handleRestartQuiz = async () => {
    if (!domainId) return

    try {
      setState(prev => ({ ...prev, isLoading: true }))

      const session = await apiClient.restartQuiz(domainId, state.quizMode)

      setState(prev => ({
        ...prev,
        session,
        currentQuestion: session.current_question || null,
        quizMode: session.quiz_mode || prev.quizMode,
        isLoading: false,
        lastResult: null,
        summary: null,
        isPaused: false
      }))
    } catch (error) {
      console.error('Failed to restart quiz:', error)
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to restart quiz',
        isLoading: false
      }))
    }
  }

  const handleExitQuiz = () => {
    navigate('/app/domains')
  }

  const handleNextQuestion = () => {
    setState(prev => ({
      ...prev,
      lastResult: null,
      currentQuestion: prev.nextQuestion,
      nextQuestion: null
    }))
  }

  const handleViewSummary = () => {
    setState(prev => ({ ...prev, showingSummary: true }))
  }

  if (state.isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (state.error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <div className="text-red-600 text-lg font-medium mb-2">Quiz Error</div>
          <p className="text-red-700 mb-4">{state.error}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={initializeQuiz}
              className="btn btn-primary"
            >
              Try Again
            </button>
            <button
              onClick={handleExitQuiz}
              className="btn btn-secondary"
            >
              Back to Domains
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Show quiz summary only after user clicks "See Results"
  if (state.showingSummary) {
    if (!state.summary) {
      return (
        <div className="flex items-center justify-center min-h-[400px]">
          <LoadingSpinner size="lg" />
        </div>
      )
    }
    return (
      <div className="max-w-4xl mx-auto">
        <QuizSummaryCard
          summary={state.summary}
          onRestart={handleRestartQuiz}
          onExit={handleExitQuiz}
        />
      </div>
    )
  }

  // Show paused state
  if (state.isPaused) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <div className="text-yellow-600 text-lg font-medium mb-2">Quiz Paused</div>
          <p className="text-yellow-700 mb-4">
            Your quiz has been paused. You can resume where you left off.
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={handleResumeQuiz}
              className="btn btn-primary"
            >
              Resume Quiz
            </button>
            <button
              onClick={handleExitQuiz}
              className="btn btn-secondary"
            >
              Exit Quiz
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!state.session || !state.currentQuestion) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
          <div className="text-gray-600 text-lg font-medium mb-2">No Questions Available</div>
          <p className="text-gray-700 mb-4">
            This domain doesn't have any questions to quiz on.
          </p>
          <button
            onClick={handleExitQuiz}
            className="btn btn-primary"
          >
            Back to Domains
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Quiz Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {state.session.domain_name}
            </h1>
            <p className="text-gray-600">
              {state.quizMode === 'reverse' ? 'Name the Term' : 'Define the Term'}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handlePauseQuiz}
              className="btn btn-secondary"
              disabled={state.isSubmitting}
            >
              Pause Quiz
            </button>
            <button
              onClick={handleExitQuiz}
              className="btn btn-outline"
            >
              Exit Quiz
            </button>
          </div>
        </div>
        
        <QuizProgress progress={state.session.progress} />
      </div>

      {/* Quiz Question */}
      <QuizQuestionCard
        question={state.currentQuestion}
        quizMode={state.quizMode}
        onSubmitAnswer={handleAnswerSubmit}
        isSubmitting={state.isSubmitting}
        lastResult={state.lastResult}
        onNextQuestion={handleNextQuestion}
        onViewSummary={handleViewSummary}
        summaryReady={!!state.summary}
      />
    </div>
  )
}

export default QuizInterface