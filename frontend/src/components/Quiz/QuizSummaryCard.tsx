import React from 'react'
import { QuizSummary } from '../../services/api'

interface QuizSummaryCardProps {
  summary: QuizSummary
  onRestart: () => void
  onExit: () => void
}

const QuizSummaryCard: React.FC<QuizSummaryCardProps> = ({
  summary,
  onRestart,
  onExit
}) => {
  const getPerformanceColor = (level: string) => {
    switch (level) {
      case 'Excellent':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'Good':
        return 'text-blue-600 bg-blue-50 border-blue-200'
      case 'Fair':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'Needs Improvement':
        return 'text-red-600 bg-red-50 border-red-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const formatTime = (minutes: number, seconds: number) => {
    if (minutes > 0) {
      return `${minutes}m ${seconds}s`
    }
    return `${seconds}s`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Quiz Complete!</h1>
        <p className="text-lg text-gray-600">{summary.domain_name}</p>
      </div>

      {/* Performance Overview */}
      <div className={`rounded-lg border-2 p-6 ${getPerformanceColor(summary.performance.performance_level)}`}>
        <div className="text-center">
          <div className="text-4xl font-bold mb-2">
            {summary.performance.accuracy_percentage}%
          </div>
          <div className="text-xl font-semibold mb-2">
            {summary.performance.performance_level}
          </div>
          <p className="text-sm opacity-90">
            {summary.performance.performance_message}
          </p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <div className="text-2xl font-bold text-gray-900">
            {summary.performance.total_questions}
          </div>
          <div className="text-sm text-gray-600">Total Questions</div>
        </div>
        
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <div className="text-2xl font-bold text-green-600">
            {summary.performance.correct_answers}
          </div>
          <div className="text-sm text-gray-600">Correct</div>
        </div>
        
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <div className="text-2xl font-bold text-red-600">
            {summary.performance.incorrect_answers}
          </div>
          <div className="text-sm text-gray-600">Incorrect</div>
        </div>
        
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <div className="text-2xl font-bold text-blue-600">
            {formatTime(summary.timing.time_taken_minutes, summary.timing.time_taken_seconds)}
          </div>
          <div className="text-sm text-gray-600">Time Taken</div>
        </div>
      </div>

      {/* Detailed Results */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Detailed Results</h3>
        <div className="space-y-4 max-h-96 overflow-y-auto">
          {summary.detailed_results.map((result, index) => {
            const isReverse = summary.quiz_mode === 'reverse'
            const questionLabel = isReverse
              ? (result.definition && result.definition.length > 120
                  ? result.definition.slice(0, 120) + '…'
                  : result.definition)
              : result.term
            const scoreDisplay = isReverse ? null : `${Math.round(result.similarity_score * 100)}%`

            return (
              <div
                key={index}
                className={`p-4 rounded-lg border ${
                  result.is_correct
                    ? 'bg-green-50 border-green-200'
                    : 'bg-red-50 border-red-200'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="font-medium text-gray-900 text-sm leading-snug pr-4">
                    {questionLabel}
                  </div>
                  <div className={`text-sm font-medium shrink-0 ${
                    result.is_correct ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {result.is_correct ? '✓' : '✗'}{scoreDisplay ? ` ${scoreDisplay}` : ''}
                  </div>
                </div>

                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">Your answer: </span>
                    <span className="text-gray-900">{result.student_answer}</span>
                  </div>

                  {!result.is_correct && (
                    <div>
                      <span className="font-medium text-gray-700">Correct answer: </span>
                      <span className="text-gray-900">{result.correct_answer}</span>
                    </div>
                  )}

                  {result.feedback && !isReverse && (
                    <div className="text-gray-600 italic">
                      {result.feedback}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-4 justify-center">
        {summary.actions.can_restart && (
          <button
            onClick={onRestart}
            className="btn btn-primary"
          >
            Take Quiz Again
          </button>
        )}
        <button
          onClick={onExit}
          className="btn btn-secondary"
        >
          Back to Domains
        </button>
      </div>
    </div>
  )
}

export default QuizSummaryCard