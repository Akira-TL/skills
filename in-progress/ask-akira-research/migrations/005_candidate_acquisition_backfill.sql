UPDATE candidates
SET acquisition_status = 'acquired',
    identity_status = 'resolved'
WHERE paper_id IS NOT NULL;
