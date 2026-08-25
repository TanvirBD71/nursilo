"""Assessment / practice domain exceptions (safe user-facing messages only)."""


class AssessmentError(Exception):
    """Base assessment error with a safe user-facing message."""

    default_message = "The request could not be completed."
    code = "error"

    def __init__(self, message: str | None = None, *, code: str | None = None):
        self.message = message or self.default_message
        self.code = code or self.code
        super().__init__(self.message)


class PracticeSetupError(AssessmentError):
    default_message = "Practice setup is invalid."
    code = "setup_invalid"


class PracticePoolEmpty(AssessmentError):
    default_message = "No published questions match this practice scope."
    code = "pool_empty"


class PracticeCapExceeded(AssessmentError):
    default_message = "Free practice limit reached. Upgrade or try again later."
    code = "cap_exceeded"


class AttemptNotFound(AssessmentError):
    default_message = "Attempt not found."
    code = "not_found"


class AttemptForbidden(AssessmentError):
    default_message = "You do not have access to this attempt."
    code = "forbidden"


class AttemptNotActive(AssessmentError):
    default_message = "This attempt is not active."
    code = "not_active"


class AttemptAlreadySubmitted(AssessmentError):
    default_message = "This attempt is already submitted."
    code = "already_submitted"


class InvalidAnswer(AssessmentError):
    default_message = "The selected answer is not valid for this question."
    code = "invalid_answer"


class InvalidNavigation(AssessmentError):
    default_message = "That question is not part of this practice attempt."
    code = "invalid_navigation"


class PracticeUnavailable(AssessmentError):
    default_message = "Practice is not available for this scope."
    code = "unavailable"


class ExamUnavailable(AssessmentError):
    default_message = "This exam is not available."
    code = "exam_unavailable"


class ExamPoolEmpty(AssessmentError):
    default_message = "This exam has no published questions available."
    code = "exam_pool_empty"


class ExamNotEntitled(AssessmentError):
    default_message = "Premium is required to start this exam."
    code = "exam_not_entitled"


class ExamExpired(AssessmentError):
    default_message = "This exam attempt has expired."
    code = "exam_expired"
