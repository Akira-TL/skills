ALTER TABLE candidates ADD COLUMN user_access_status TEXT NOT NULL DEFAULT 'not_required'
    CHECK (user_access_status IN (
        'not_required', 'required', 'completed', 'declined', 'unavailable_to_user'
    ));
ALTER TABLE candidates ADD COLUMN user_access_reason TEXT;
