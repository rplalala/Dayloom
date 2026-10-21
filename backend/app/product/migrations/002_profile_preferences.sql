CREATE FUNCTION app.unique_text_values(values_array text[]) RETURNS boolean
LANGUAGE sql IMMUTABLE STRICT AS $$
    SELECT count(*) = count(DISTINCT value) AND bool_and(value IS NOT NULL)
    FROM unnest(values_array) AS value
$$;
ALTER TABLE app.user_profiles
    ADD COLUMN currency text NOT NULL DEFAULT 'AUD'
        CHECK (currency IN ('AUD','USD','EUR','GBP','CNY','JPY','CAD','NZD','SGD','HKD',
            'CHF','KRW','INR','THB','MYR','IDR','VND','PHP','AED','ZAR')),
    ADD COLUMN interests text[] NOT NULL DEFAULT '{}'
        CHECK (interests <@ ARRAY['City walks','History & culture','Art & museums','Nature',
            'Local food','Photography','Family experiences','Free exploration']::text[]
            AND app.unique_text_values(interests)),
    ADD COLUMN pace text CHECK (pace IN ('relaxed','balanced','rich')),
    ADD COLUMN transport text[] NOT NULL DEFAULT '{}'
        CHECK (transport <@ ARRAY['walk','transit','drive']::text[]
            AND app.unique_text_values(transport)),
    ADD COLUMN notes text NOT NULL DEFAULT '' CHECK (length(notes) <= 24000);
