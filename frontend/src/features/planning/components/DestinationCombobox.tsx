import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { getDestinationSuggestions, type DestinationSuggestion } from "../api";

interface DestinationComboboxProps {
  value: string;
  onChange: (value: string) => void;
  onSelect?: () => void;
  disabled: boolean;
  label?: ReactNode;
  placeholder?: string;
}

export function DestinationCombobox({ value, onChange, onSelect, disabled, label = "Destination", placeholder = "Beijing" }: DestinationComboboxProps) {
  const [choices, setChoices] = useState<DestinationSuggestion[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [notice, setNotice] = useState("");
  const [composing, setComposing] = useState(false);
  const listId = useId();
  const attempts = useRef(0);
  const lastSend = useRef(Number.NEGATIVE_INFINITY);
  const selectedLabel = useRef<string | null>(null);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const prefix = value.trim();
    if (disabled || composing || prefix.length < 2 || prefix.length > 100 || selectedLabel.current === value) {
      return () => { active = false; controller.abort(); };
    }
    const timer = window.setTimeout(() => {
      if (attempts.current >= 20) {
        setNotice("You can enter a destination manually; suggestion requests are limited.");
        return;
      }
      const now = Date.now();
      if (now < lastSend.current + 1100) {
        setNotice("You can enter a destination manually; suggestions are temporarily limited.");
        return;
      }
      attempts.current += 1;
      lastSend.current = now;
      void getDestinationSuggestions(prefix, controller.signal).then(result => {
        if (!active) return;
        setChoices(result.suggestions);
        setActiveIndex(-1);
        setNotice(result.suggestions.length ? "" : "No city suggestions. You can enter a destination manually.");
      }).catch(() => {
        if (!active) return;
        setChoices([]);
        setNotice("Suggestions are unavailable. You can enter a destination manually.");
      });
    }, 500);
    return () => { active = false; window.clearTimeout(timer); controller.abort(); };
  }, [value, disabled, composing]);

  function choose(choice: DestinationSuggestion) {
    selectedLabel.current = choice.label;
    setChoices([]);
    setNotice("");
    setActiveIndex(-1);
    onChange(choice.label);
    onSelect?.();
  }

  return <div className="destination-control field-wide">
    <label>{label}
      <input aria-label="Destination" type="text" role="combobox" aria-autocomplete="list" aria-controls={listId}
        aria-expanded={choices.length > 0} aria-activedescendant={activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined}
        value={value} required disabled={disabled} placeholder={placeholder}
        onChange={event => {
          selectedLabel.current = null;
          setChoices([]);
          setNotice("");
          setActiveIndex(-1);
          onChange(event.target.value);
        }}
        onCompositionStart={() => setComposing(true)}
        onCompositionEnd={() => setComposing(false)}
        onKeyDown={event => {
          if (event.key === "Escape") { setChoices([]); setActiveIndex(-1); return; }
          if (event.key === "ArrowDown" && choices.length) {
            event.preventDefault();
            setActiveIndex(index => Math.min(index + 1, choices.length - 1));
          } else if (event.key === "ArrowUp" && choices.length) {
            event.preventDefault();
            setActiveIndex(index => Math.max(index - 1, 0));
          } else if (event.key === "Enter" && activeIndex >= 0 && choices[activeIndex]) {
            event.preventDefault();
            choose(choices[activeIndex]);
          }
        }} />
    </label>
    {choices.length > 0 && <div id={listId} className="destination-options" role="listbox" aria-label="City suggestions">
      {choices.map((choice, index) => <button type="button" role="option" key={choice.id}
        id={`${listId}-${index}`} aria-selected={index === activeIndex}
        onMouseDown={event => event.preventDefault()} onClick={() => choose(choice)}>
        {choice.label}
      </button>)}
    </div>}
    {notice && <p className="field-help" aria-live="polite">{notice}</p>}
  </div>;
}
