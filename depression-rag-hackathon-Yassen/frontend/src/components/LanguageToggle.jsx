import { useLanguage } from '../i18n'

export default function LanguageToggle() {
  const { lang, setLang, t } = useLanguage()
  return (
    <div className="lang-toggle" role="group" aria-label="English or Egyptian Arabic">
      <button
        type="button"
        className={`lang-btn ${lang === 'en' ? 'active' : ''}`}
        onClick={() => setLang('en')}
      >
        {t.langEn}
      </button>
      <button
        type="button"
        className={`lang-btn ${lang === 'arz' ? 'active' : ''}`}
        onClick={() => setLang('arz')}
      >
        {t.langAr}
      </button>
    </div>
  )
}
