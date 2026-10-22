import React, { useState, useMemo, useRef, useEffect } from "react";
import styles from "./LanguageSelector.module.css";
import { Language } from "@/types";

export interface LanguageSelectorProps {
  languages: Language[];
  selectedCode: string | null;
  onSelect: (language: Language) => void;
  label?: string;
  placeholder?: string;
  disabled?: boolean;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  languages,
  selectedCode,
  onSelect,
  label,
  placeholder = "Select a language...",
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedLanguage = useMemo(
    () => languages.find((lang) => lang.code === selectedCode) || null,
    [languages, selectedCode]
  );

  const filteredLanguages = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return languages;
    return languages.filter(
      (lang) =>
        lang.name.toLowerCase().includes(q) ||
        lang.native_name.toLowerCase().includes(q) ||
        lang.code.toLowerCase().includes(q)
    );
  }, [languages, search]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className={styles.container} ref={containerRef}>
      {label && <label className={styles.label}>{label}</label>}

      <button
        type="button"
        className={styles.selectTrigger}
        onClick={() => !disabled && setIsOpen((prev) => !prev)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <div className={styles.triggerText}>
          {selectedLanguage ? (
            <>
              <span className={styles.primaryName}>{selectedLanguage.name}</span>
              <span className={styles.nativeName}>({selectedLanguage.native_name})</span>
              {selectedLanguage.is_rtl && <span className={styles.rtlBadge}>RTL</span>}
            </>
          ) : (
            <span className={styles.nativeName}>{placeholder}</span>
          )}
        </div>
        <span aria-hidden="true">▾</span>
      </button>

      {isOpen && (
        <div className={styles.dropdown} role="listbox">
          <div className={styles.searchBox}>
            <input
              type="text"
              className={styles.searchInput}
              placeholder="Search language or script..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>

          <div className={styles.optionsList}>
            {filteredLanguages.length > 0 ? (
              filteredLanguages.map((lang) => {
                const isSelected = lang.code === selectedCode;
                return (
                  <button
                    key={lang.code}
                    type="button"
                    className={`${styles.optionItem} ${isSelected ? styles.optionItemSelected : ""}`}
                    onClick={() => {
                      onSelect(lang);
                      setIsOpen(false);
                      setSearch("");
                    }}
                    role="option"
                    aria-selected={isSelected}
                  >
                    <div className={styles.optionContent}>
                      <div className={styles.optionHeader}>
                        <span className={styles.primaryName}>{lang.name}</span>
                        <span className={styles.nativeName}>({lang.native_name})</span>
                        {lang.is_rtl && <span className={styles.rtlBadge}>RTL</span>}
                      </div>
                      <span className={styles.optionSub}>
                        Code: {lang.code} · Script: {lang.script_code}
                      </span>
                    </div>
                  </button>
                );
              })
            ) : (
              <div className={styles.emptyState}>No matching languages found.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
