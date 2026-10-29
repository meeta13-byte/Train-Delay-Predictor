// Type-to-search dropdown. Typing filters the list and puts the best matches on top:
// exact code/number first, then names that start with the text, then words that start
// with it, then anything that contains it.

import { useEffect, useId, useMemo, useRef, useState } from 'react';

const norm = (s) => String(s ?? '').toLowerCase().trim();

/** Rank options for a query. options: [{ value, label, hint?, keys?: string[] }] */
export function rankOptions(options, query, limit = 60) {
  const q = norm(query);
  if (!q) return options.slice(0, limit);
  const scored = [];
  for (const o of options) {
    const keys = [o.value, ...(o.keys || [])].map(norm);
    const label = norm(o.label);
    let score = null;
    if (keys.includes(q)) score = 0;
    else if (label.startsWith(q) || keys.some((k) => k.startsWith(q))) score = 1;
    else if (label.split(/[\s·()/-]+/).some((w) => w.startsWith(q))) score = 2;
    else if (label.includes(q) || keys.some((k) => k.includes(q))) score = 3;
    if (score !== null) scored.push([score, o]);
  }
  scored.sort((a, b) => a[0] - b[0]);
  return scored.slice(0, limit).map(([, o]) => o);
}

export default function Combobox({ id, label, options, value, onChange, placeholder = 'Type to search', emptyText = 'No matches', clearLabel, className = '' }) {
  const autoId = useId();
  const inputId = id || `cb${autoId}`;
  const listId = `${inputId}-list`;
  const selected = options.find((o) => String(o.value) === String(value));
  const [text, setText] = useState(selected?.label ?? '');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [typing, setTyping] = useState(false);
  const listRef = useRef(null);

  // keep the box in sync when the value changes from outside (e.g. reset)
  useEffect(() => {
    if (!typing) setText(selected?.label ?? '');
  }, [selected, typing]);

  const matches = useMemo(() => {
    const ranked = rankOptions(options, typing ? text : '');
    return clearLabel ? [{ value: '', label: clearLabel, clear: true }, ...ranked] : ranked;
  }, [options, text, typing, clearLabel]);

  useEffect(() => {
    setActive(clearLabel && typing && text ? 1 : 0);
  }, [text, typing, clearLabel]);

  useEffect(() => {
    listRef.current?.querySelector(`[data-i="${active}"]`)?.scrollIntoView({ block: 'nearest' });
  }, [active, open]);

  const choose = (o) => {
    onChange(o ? String(o.value) : '');
    setText(o && !o.clear ? o.label : '');
    setTyping(false);
    setOpen(false);
  };

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOpen(true);
      setActive((a) => Math.min(a + 1, matches.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === 'Enter' && open) {
      e.preventDefault();
      if (matches[active]) choose(matches[active]);
    } else if (e.key === 'Escape') {
      setTyping(false);
      setOpen(false);
      setText(selected?.label ?? '');
    }
  };

  const onBlur = () => {
    // accept a typed exact code / number even without picking from the list
    if (typing) {
      const exact = text && rankOptions(options, text, 1)[0];
      if (exact && [exact.value, ...(exact.keys || [])].map(norm).includes(norm(text))) choose(exact);
      else if (!text) choose(null);
      else {
        setTyping(false);
        setText(selected?.label ?? '');
      }
    }
    setOpen(false);
  };

  return (
    <div className={`field combo ${className}`}>
      <label htmlFor={inputId}>{label}</label>
      <input
        id={inputId}
        className="input combo-input"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && matches[active] ? `${inputId}-o${active}` : undefined}
        autoComplete="off"
        spellCheck={false}
        placeholder={placeholder}
        value={text}
        onFocus={(e) => {
          setOpen(true);
          e.target.select();
        }}
        onClick={() => setOpen(true)}
        onChange={(e) => {
          setText(e.target.value);
          setTyping(true);
          setOpen(true);
        }}
        onKeyDown={onKeyDown}
        onBlur={onBlur}
      />
      {open && (
        <ul id={listId} ref={listRef} className="combo-menu" role="listbox" aria-label={label}>
          {matches.length === 0 && <li className="combo-empty">{emptyText}</li>}
          {matches.map((o, i) => (
            <li
              key={`${o.value}-${i}`}
              id={`${inputId}-o${i}`}
              data-i={i}
              role="option"
              aria-selected={i === active}
              className={`combo-option${i === active ? ' active' : ''}${o.clear ? ' clear' : ''}`}
              onMouseDown={(e) => {
                e.preventDefault(); // keep focus so blur doesn't fire first
                choose(o);
              }}
              onMouseEnter={() => setActive(i)}
            >
              <span>{o.label}</span>
              {o.hint && <small>{o.hint}</small>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
