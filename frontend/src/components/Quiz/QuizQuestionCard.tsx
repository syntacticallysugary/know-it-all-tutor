import React, { useState, useEffect } from 'react'
import type { QuizQuestion, AnswerResult } from '../../services/api'

interface QuizQuestionCardProps {
  question: QuizQuestion
  quizMode: 'forward' | 'reverse'
  onSubmitAnswer: (answer: string) => void
  isSubmitting: boolean
  lastResult: AnswerResult | null
  onNextQuestion: () => void
  onViewSummary?: () => void
  summaryReady?: boolean
}

const QuizQuestionCard: React.FC<QuizQuestionCardProps> = ({
  question,
  quizMode,
  onSubmitAnswer,
  isSubmitting,
  lastResult,
  onNextQuestion,
  onViewSummary,
  summaryReady = false
}) => {
  const [answer, setAnswer] = useState('')
  const [submittedAnswer, setSubmittedAnswer] = useState('')
  const [showResult, setShowResult] = useState(false)

  // Show result when we get a new result
  useEffect(() => {
    if (lastResult) {
      setShowResult(true)
      setAnswer('') // Clear the input for next question
    } else {
      setShowResult(false)
    }
  }, [lastResult])

  // Reset result display when question changes
  useEffect(() => {
    if (!lastResult) {
      setShowResult(false)
    }
  }, [question.term_id, lastResult])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (answer.trim() && !isSubmitting) {
      setSubmittedAnswer(answer.trim())
      onSubmitAnswer(answer.trim())
    }
  }

  const handleNextQuestion = () => {
    setShowResult(false)
    onNextQuestion()
  }

  const getResultColor = (isCorrect: boolean, similarityScore: number) => {
    if (isCorrect) return 'text-green-600'
    if (similarityScore >= 0.5) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getResultIcon = (isCorrect: boolean, similarityScore: number) => {
    if (isCorrect) return '✓'
    if (similarityScore >= 0.5) return '~'
    return '✗'
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
      {/* Question Display */}
      <div className="text-center mb-8">
        <div className="text-sm text-gray-500 mb-2">
          Question {question.question_number} of {question.total_questions}
        </div>
        {quizMode === 'reverse' ? (
          <>
            <div className="text-base text-gray-700 leading-relaxed mb-4 max-w-2xl mx-auto text-left bg-gray-50 rounded-lg p-4 border border-gray-200">
              {question.definition}
            </div>
            <div className="text-lg text-gray-600">
              What term is described by this definition?
            </div>
          </>
        ) : (
          <>
            <div className="text-3xl font-bold text-gray-900 mb-4">
              {question.term}
            </div>
            <div className="text-lg text-gray-600">
              What is the definition of this term?
            </div>
          </>
        )}
      </div>

      {/* Answer Input or Result Display */}
      {showResult && lastResult ? (
        <div className="space-y-6">
          {/* Result Feedback */}
          <div className={`text-center p-6 rounded-lg border-2 ${
            lastResult.evaluation.is_correct 
              ? 'bg-green-50 border-green-200' 
              : lastResult.evaluation.similarity_score >= 0.5
                ? 'bg-yellow-50 border-yellow-200'
                : 'bg-red-50 border-red-200'
          }`}>
            <div className={`text-4xl mb-2 ${getResultColor(
              lastResult.evaluation.is_correct, 
              lastResult.evaluation.similarity_score
            )}`}>
              {getResultIcon(lastResult.evaluation.is_correct, lastResult.evaluation.similarity_score)}
            </div>
            <div className={`text-xl font-semibold mb-2 ${getResultColor(
              lastResult.evaluation.is_correct, 
              lastResult.evaluation.similarity_score
            )}`}>
              {lastResult.evaluation.is_correct ? 'Correct!' : 
               lastResult.evaluation.similarity_score >= 0.5 ? 'Close!' : 'Incorrect'}
            </div>
            <div className="text-gray-700 mb-3">
              {lastResult.evaluation.feedback}
            </div>
            {quizMode === 'forward' && (
              <div className="text-sm text-gray-600">
                Similarity Score: {Math.round(lastResult.evaluation.similarity_score * 100)}%
              </div>
            )}
          </div>

          {/* Your Answer Display */}
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="text-sm font-medium text-gray-700 mb-2">Your Answer:</div>
            <div className="text-gray-900">{submittedAnswer}</div>
          </div>

          {/* Correct Answer Display */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm font-medium text-gray-700 mb-2">Correct Answer:</div>
            <div className="text-gray-900">{lastResult.evaluation.correct_answer}</div>
          </div>

          {/* Next Question / See Results Button */}
          {lastResult.next_question ? (
            <div className="text-center">
              <button
                onClick={handleNextQuestion}
                className="btn btn-primary btn-lg"
              >
                Next Question
              </button>
            </div>
          ) : (
            <div className="text-center">
              <div className="text-lg font-semibold text-gray-900 mb-4">
                Quiz Complete!
              </div>
              <button
                onClick={onViewSummary}
                disabled={!summaryReady}
                className="btn btn-primary btn-lg min-w-[200px]"
              >
                {summaryReady ? 'See Results' : (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Loading Results...
                  </div>
                )}
              </button>
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Answer Input */}
          <div>
            <label htmlFor="answer" className="block text-sm font-medium text-gray-700 mb-2">
              Your Answer
            </label>
            {quizMode === 'reverse' ? (
              <input
                id="answer"
                type="text"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Enter the term..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={isSubmitting}
                autoComplete="off"
                required
              />
            ) : (
              <textarea
                id="answer"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Enter your definition here..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                rows={4}
                disabled={isSubmitting}
                required
              />
            )}
          </div>

          {/* Submit Button */}
          <div className="text-center">
            <button
              type="submit"
              disabled={!answer.trim() || isSubmitting}
              className="btn btn-primary btn-lg min-w-[200px]"
            >
              {isSubmitting ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Evaluating...
                </div>
              ) : (
                'Submit Answer'
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

export default QuizQuestionCard