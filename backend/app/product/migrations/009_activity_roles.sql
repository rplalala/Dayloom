-- Missing historical roles remain unknown; display themes confer no place authority.
ALTER TABLE app.trip_activities
    ADD COLUMN activity_kind text NOT NULL DEFAULT 'unknown'
        CHECK (activity_kind IN ('main_poi','generic_activity','transport','free_time','unknown')),
    ADD COLUMN atmosphere_theme text
        CHECK (atmosphere_theme IN ('meal','rest','explore','walk','general'));
