import { AuthService } from './auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api'

export interface Domain {
  id: string
  name: string
  description: string
  term_count: number
  user_id: string
  created_at?: string
  updated_at?: string
}

export interface Term {
  id: string
  term: string
  definition: string
  created_at?: string
  updated_at?: string
}

/**
 * Learning streak information for a user.
 */
export interface LearningStreak {
  current_streak: number
  longest_streak: number
  last_activity_date: string | null
}

export interface DashboardData {
  user_id: string
  total_domains: number
  domains: DomainProgress[]
  overall_stats: {
    total_terms: number
    mastered_terms: number
    proficient_terms: number
    developing_terms: number
    needs_practice_terms: number
    not_attempted_terms: number
    overall_completion_percentage: number
    overall_mastery_percentage: number
  }
  recent_activity: RecentActivity[]
  learning_streaks: LearningStreak
}

export interface DomainProgress {
  id: string
  name: string
  description: string
  term_count: number
  completion_percentage: number
  mastery_percentage: number
  mastery_breakdown: {
    mastered: number
    proficient: number
    developing: number
    needs_practice: number
    not_attempted: number
  }
  last_activity?: string
}

export interface RecentActivity {
  timestamp: string
  is_correct: boolean
  similarity_score: number
  term: string
  domain_name: string
}

export interface CreateDomainRequest {
  name: string
  description: string
}

export interface AddTermsRequest {
  terms: {
    term: string
    definition: string
  }[]
}

export interface QuizSession {
  session_id: string
  status: 'started' | 'resumed' | 'paused' | 'completed'
  domain_name: string
  quiz_mode: 'forward' | 'reverse'
  current_question?: QuizQuestion
  progress: QuizProgress
  quiz_completed?: boolean
}

export interface QuizQuestion {
  term_id: string
  term?: string
  definition?: string
  question_number: number
  total_questions: number
}

export interface QuizProgress {
  current_index: number
  total_questions: number
  correct_answers?: number
  completed: boolean
}

export interface AnswerSubmission {
  session_id: string
  answer: string
}

export interface AnswerResult {
  session_id: string
  evaluation: {
    is_correct: boolean
    similarity_score: number
    feedback: string
    correct_answer: string
  }
  progress: QuizProgress & { correct_answers: number }
  next_question?: QuizQuestion
  quiz_completed: boolean
}

export interface QuizSummary {
  session_id: string
  domain_name: string
  quiz_mode: 'forward' | 'reverse'
  status: 'completed'
  completion_time: string
  performance: {
    total_questions: number
    correct_answers: number
    incorrect_answers: number
    accuracy_percentage: number
    average_similarity_score: number
    performance_level: string
    performance_message: string
  }
  timing: {
    time_taken_minutes: number
    time_taken_seconds: number
    total_seconds: number
  }
  detailed_results: Array<{
    term: string
    definition?: string
    student_answer: string
    correct_answer: string
    is_correct: boolean
    similarity_score: number
    feedback: string
  }>
  actions: {
    can_restart: boolean
    can_review: boolean
  }
}

class APIClient {
  private async getAuthHeaders(): Promise<HeadersInit> {
    // Use the enhanced AuthService for environment-aware authentication
    return AuthService.getAuthHeaders()
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers = await this.getAuthHeaders()
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        ...headers,
        ...options.headers,
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.message || errorData.error?.message || `HTTP ${response.status}: ${response.statusText}`)
    }

    const json = await response.json()
    
    // Handle backend response structure: {success: true, data: {...}}
    if (json.success && json.data !== undefined) {
      return json.data as T
    }
    
    // Fallback for direct responses
    return json as T
  }

  // Dashboard API
  async getDashboard(): Promise<DashboardData> {
    return this.request<DashboardData>('/progress/dashboard')
  }

  // Domain Management API
  async getDomains(): Promise<Domain[]> {
    const response = await this.request<{domains: Domain[], count: number}>('/domains')
    return response.domains
  }

  async getDomain(domainId: string): Promise<Domain> {
    return this.request<Domain>(`/domains/${domainId}`)
  }

  async createDomain(data: CreateDomainRequest): Promise<Domain> {
    return this.request<Domain>('/domains', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateDomain(domainId: string, data: Partial<CreateDomainRequest>): Promise<{ id: string }> {
    return this.request<{ id: string }>(`/domains/${domainId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteDomain(domainId: string): Promise<{ id: string }> {
    return this.request<{ id: string }>(`/domains/${domainId}`, {
      method: 'DELETE',
    })
  }

  // Term Management API
  async getTerms(domainId: string): Promise<Term[]> {
    return this.request<Term[]>(`/domains/${domainId}/terms`)
  }

  async addTerms(domainId: string, data: AddTermsRequest): Promise<{ terms: Term[], count: number }> {
    return this.request<{ terms: Term[], count: number }>(`/domains/${domainId}/terms`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateTerm(domainId: string, termId: string, data: Partial<Term>): Promise<{ id: string }> {
    return this.request<{ id: string }>(`/domains/${domainId}/terms/${termId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteTerm(domainId: string, termId: string): Promise<{ id: string }> {
    return this.request<{ id: string }>(`/domains/${domainId}/terms/${termId}`, {
      method: 'DELETE',
    })
  }

  // Quiz API
  async startQuiz(domainId: string, quizMode: 'forward' | 'reverse' = 'forward'): Promise<QuizSession> {
    return this.request<QuizSession>('/quiz/start', {
      method: 'POST',
      body: JSON.stringify({ domain_id: domainId, quiz_mode: quizMode }),
    })
  }

  async submitAnswer(submission: AnswerSubmission): Promise<AnswerResult> {
    return this.request<AnswerResult>('/quiz/answer', {
      method: 'POST',
      body: JSON.stringify(submission),
    })
  }

  async pauseQuiz(sessionId: string): Promise<{ session_id: string; status: string; message: string }> {
    return this.request<{ session_id: string; status: string; message: string }>('/quiz/pause', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    })
  }

  async resumeQuiz(sessionId: string): Promise<QuizSession> {
    return this.request<QuizSession>('/quiz/resume', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    })
  }

  async restartQuiz(domainId: string, quizMode: 'forward' | 'reverse' = 'forward'): Promise<QuizSession> {
    return this.request<QuizSession>('/quiz/restart', {
      method: 'POST',
      body: JSON.stringify({ domain_id: domainId, quiz_mode: quizMode }),
    })
  }

  async getQuizSummary(sessionId: string): Promise<QuizSummary> {
    return this.request<QuizSummary>(`/quiz/complete?session_id=${sessionId}`)
  }

  /**
   * Validate a batch upload file before processing.
   * 
   * @param batchData The parsed JSON data from the upload file.
   * @returns Validation results including any duplicates or warnings.
   */
  async validateBatchUpload(batchData: Record<string, any>): Promise<BatchValidationResult> {
    return this.request<BatchValidationResult>('/batch/validate', {
      method: 'POST',
      body: JSON.stringify({ batch_data: batchData }),
    })
  }

  /**
   * Process a batch upload of domains and terms.
   * 
   * @param batchData The parsed JSON data from the upload file.
   * @param overwrite Whether to overwrite existing domains/terms.
   * @returns Results of the upload process.
   */
  async processBatchUpload(batchData: Record<string, any>, overwrite: boolean = false): Promise<BatchUploadResult> {
    return this.request<BatchUploadResult>('/batch/upload', {
      method: 'POST',
      body: JSON.stringify({ batch_data: batchData, overwrite }),
    })
  }

  async getUploadHistory(): Promise<UploadHistoryItem[]> {
    return this.request<UploadHistoryItem[]>('/batch/history')
  }
}

export interface BatchValidationResult {
  valid: boolean
  total_domains: number
  total_terms: number
  existing_duplicates: string[]
  warnings: string[]
}

export interface BatchUploadResult {
  upload_id: string
  domains_created: number
  terms_created: number
  terms_updated: number
  domains_skipped: number
  processing_summary: string[]
}

export interface UploadHistoryItem {
  id: string
  filename: string
  subject_count: number
  status: 'completed' | 'failed' | 'processing'
  uploaded_at: string
  processed_at?: string
  error_message?: string
  metadata: {
    domains_created: number
    terms_created: number
    total_items: number
  }
}

export interface PendingUser {
  username: string
  email: string
  given_name: string
  family_name: string
  created_at: string
}

class AdminAPIClient {
  private async getAuthHeaders(): Promise<HeadersInit> {
    return AuthService.getAuthHeaders()
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: { ...headers, ...options.headers },
    })
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || `HTTP ${response.status}`)
    }
    return response.json() as Promise<T>
  }

  async getPendingUsers(): Promise<PendingUser[]> {
    const data = await this.request<{ users: PendingUser[] }>('/admin/users/pending')
    return data.users
  }

  async approveUser(username: string): Promise<void> {
    await this.request(`/admin/users/${encodeURIComponent(username)}/approve`, { method: 'POST' })
  }

  async denyUser(username: string, reason?: string): Promise<void> {
    await this.request(`/admin/users/${encodeURIComponent(username)}/deny`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason || '' }),
    })
  }
}

export const apiClient = new APIClient()
export const adminApiClient = new AdminAPIClient()
