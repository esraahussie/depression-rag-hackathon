import React from 'react'

const STRINGS = {
  en: {
    langEn: 'EN',
    langAr: 'مصري',
    tagline: 'Clinical RAG for depression guidelines',
    chat: 'Chat',
    status: 'AI Assistant · RAG-powered',
    chatTitle: 'Depression Assistant',
    chatSubtitle: 'Evidence-based depression information and support.',
    autoRead: 'Auto-read replies aloud',
    emptyTitle: 'How can I help you today?',
    emptyBody: 'Ask about depression symptoms, treatments, screening, or how to support others.',
    examples: [
      'What are the common symptoms of depression?',
      'What treatments are available for depression?',
      'What is the PHQ-9?',
      'How can I support someone experiencing depression?',
    ],
    placeholder: 'Ask a question about depression...',
    listening: 'Listening...',
    startMic: 'Speak',
    stopMic: 'Stop listening',
    send: 'Send',
    disclaimer:
      'This assistant provides educational information and is not a substitute for professional medical advice.',
    confidence: 'Confidence',
    sources: 'Supporting Sources',
    additional: 'Additional Retrieved Sources',
    page: 'Page',
    chunk: 'Chunk',
    relevance: 'Relevance',
    openSource: 'Open guideline',
    error:
      'Sorry, I could not process your request right now. Please ensure the backend server is running and try again.',
    readAloud: 'Read answer aloud',
    stopReading: 'Stop reading aloud',
    phqTitle: 'PHQ-9 Depression Screening',
    phqSubtitle:
      'Over the last 2 weeks, how often have you been bothered by any of the following problems?',
    gadTitle: 'GAD-7 Anxiety Screening',
    gadSubtitle:
      'Over the last 2 weeks, how often have you been bothered by any of the following problems?',
    epdsTitle: 'EPDS Postnatal Depression Screening',
    epdsSubtitle:
      'As you are pregnant or have recently had a baby, tell us how you have felt over the past 7 days, not just how you feel today.',
    question: 'Question',
    sensitive: 'Sensitive',
    calculate: 'Calculate Score',
    startOver: 'Start Over',
    answerQuestion: (n) => `Please answer question ${n} before calculating your score.`,
    yourScore: (name) => `Your ${name} Score`,
    askGuideline: 'Ask the guideline about this score',
    safetyTitle: 'Your safety matters.',
    safetyBody:
      'You indicated having thoughts of self-harm. Please reach out to a mental health professional, a trusted person, or emergency services immediately if you are in danger.',
    crisisResources:
      'In Egypt, call emergency services on 123. If you are in immediate danger, go to the nearest emergency department.',
    screeningNotDiagnosis: (name) =>
      `The ${name} is a screening tool and does not by itself provide a clinical diagnosis. Consider discussing your results with a qualified healthcare professional.`,
    frequency: ['Not at all', 'Several days', 'More than half the days', 'Nearly every day'],
    phqItems: [
      'Little interest or pleasure in doing things',
      'Feeling down, depressed, or hopeless',
      'Trouble falling or staying asleep, or sleeping too much',
      'Feeling tired or having little energy',
      'Poor appetite or overeating',
      'Feeling bad about yourself — or that you are a failure or have let yourself or your family down',
      'Trouble concentrating on things, such as reading the newspaper or watching television',
      'Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual',
      'Thoughts that you would be better off dead or of hurting yourself in some way',
    ],
    gadItems: [
      'Feeling nervous, anxious, or on edge',
      'Not being able to stop or control worrying',
      'Worrying too much about different things',
      'Trouble relaxing',
      'Being so restless that it is hard to sit still',
      'Becoming easily annoyed or irritable',
      'Feeling afraid as if something awful might happen',
    ],
  },
  arz: {
    langEn: 'EN',
    langAr: 'مصري',
    tagline: 'مساعد طبي بالمصري من الإرشادات',
    chat: 'الدردشة',
    status: 'مساعد ذكي · بيرد بالمصري من الأدلة',
    chatTitle: 'مساعد الاكتئاب',
    chatSubtitle: 'هجاوبك بالمصري من إرشادات WHO و NICE — ومن غير تشخيص.',
    autoRead: 'اقرأ الردود بصوت عالي',
    emptyTitle: 'تحب أساعدك في إيه النهارده؟',
    emptyBody: 'اسأل عن أعراض الاكتئاب، العلاج، الفحوصات، أو إزاي تساند حد قريب منك.',
    examples: [
      'إيه أعراض الاكتئاب الشائعة؟',
      'إيه علاجات الاكتئاب المتاحة؟',
      'إيه هو مقياس PHQ-9؟',
      'إزاي أساعد حد عنده اكتئاب؟',
    ],
    placeholder: 'اكتب سؤالك بالمصري أو الإنجليزي...',
    listening: 'بسمعك...',
    startMic: 'اتكلم',
    stopMic: 'وقف التسجيل',
    send: 'ابعت',
    disclaimer:
      'المساعد ده للمعلومة والتوعية، ومش بديل عن كشف عند دكتور.',
    confidence: 'الثقة في الرد',
    sources: 'المصادر اللي اتعمدت عليها',
    additional: 'مصادر اتجابت كمان',
    page: 'صفحة',
    chunk: 'مقطع',
    relevance: 'الصلة',
    openSource: 'افتح الإرشاد',
    error: 'مقدرش أكمّل دلوقتي. تأكد إن السيرفر شغال وجرّب تاني.',
    readAloud: 'اسمع الرد',
    stopReading: 'وقف القراءة',
    phqTitle: 'فحص الاكتئاب PHQ-9',
    phqSubtitle: 'خلال الأسبوعين اللي فاتوا، كل قد إيه ضايقتك المشكلات دي؟',
    gadTitle: 'فحص القلق GAD-7',
    gadSubtitle: 'خلال الأسبوعين اللي فاتوا، كل قد إيه ضايقتك المشكلات دي؟',
    epdsTitle: 'فحص اكتئاب ما بعد الولادة EPDS',
    epdsSubtitle:
      'لو أنتِ حامل أو خلفتي قريب، قولي إحساسك خلال آخر 7 أيام، مش بس النهارده.',
    question: 'سؤال',
    sensitive: 'حساس',
    calculate: 'احسب نتيجتك',
    startOver: 'ابدأ من الأول',
    answerQuestion: (n) => `جاوب سؤال ${n} الأول عشان أحسب النتيجة.`,
    yourScore: (name) => `نتيجة ${name}`,
    askGuideline: 'اسأل الإرشاد الطبي عن النتيجة دي',
    safetyTitle: 'سلامتك مهمة.',
    safetyBody:
      'وضحت إن عندك أفكار إيذاء للنفس. كلّم مختص صحة نفسية أو حد تثق فيه أو خدمات الطوارئ فوراً لو في خطر.',
    crisisResources:
      'في مصر اتصل بالطوارئ على 123. لو الخطر فوري، روح أقرب قسم استقبال.',
    screeningNotDiagnosis: (name) =>
      `${name} أداة فحص بس، مش تشخيص. كلم دكتور أو مختص عن النتيجة.`,
    frequency: ['أبداً', 'عدة أيام', 'أكثر من نصف الأيام', 'تقريباً كل يوم'],
    phqItems: [
      'قلة الاهتمام أو المتعة في أداء الأشياء',
      'الشعور بالحزن أو الاكتئاب أو اليأس',
      'صعوبة في النوم أو النوم أكثر من المعتاد أو النوم المتواصل',
      'الشعور بالتعب أو قلة الطاقة',
      'ضعف الشهية أو الإفراط في الأكل',
      'الشعور بالسوء تجاه نفسك — أو أنك فاشل أو أنك خذلت نفسك أو عائلتك',
      'صعوبة التركيز على الأشياء، مثل قراءة الجريدة أو مشاهدة التلفزيون',
      'التحرك أو التحدث ببطء لدرجة أن الآخرين لاحظوا ذلك؟ أو العكس — التململ أو الحركة الزائدة أكثر من المعتاد',
      'أفكار بأنك ستكون أفضل لو كنت ميتاً، أو إيذاء نفسك بطريقة ما',
    ],
    gadItems: [
      'الشعور بالتوتر أو القلق أو العصبية',
      'عدم القدرة على إيقاف أو التحكم في القلق',
      'القلق الزائد حول أشياء مختلفة',
      'صعوبة في الاسترخاء',
      'التململ لدرجة يصعب معها الجلوس بهدوء',
      'سهولة الانزعاج أو الغضب',
      'الشعور بالخوف كأن شيئاً مريعاً سيحدث',
    ],
  },
}

const LanguageContext = React.createContext(null)

export function LanguageProvider({ children }) {
  const [lang, setLang] = React.useState(() => {
    try {
      return localStorage.getItem('mindcare-lang') || 'en'
    } catch {
      return 'en'
    }
  })

  React.useEffect(() => {
    const arabic = lang === 'arz'
    document.documentElement.lang = arabic ? 'ar' : 'en'
    document.documentElement.dir = arabic ? 'rtl' : 'ltr'
    try {
      localStorage.setItem('mindcare-lang', lang)
    } catch {
      /* ignore */
    }
  }, [lang])

  const value = React.useMemo(() => {
    const base = STRINGS[lang] || STRINGS.en
    return {
      lang,
      setLang,
      isAr: lang === 'arz',
      t: {
        ...base,
        assistantStatus: base.status,
        pageTitle: base.chatTitle,
        pageSubtitle: base.chatSubtitle,
        supportingSources: base.sources,
        additionalSources: base.additional,
        crisisTitle: base.safetyTitle,
        crisisBody: base.safetyBody,
        screeningDisclaimer: base.screeningNotDiagnosis,
        phqOptions: (base.frequency || []).map((label, value) => ({ label, value })),
        epdsItems: EPDS_BY_LANG[lang] || EPDS_BY_LANG.en,
      },
    }
  }, [lang])

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const ctx = React.useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used inside LanguageProvider')
  return ctx
}

export const EPDS_BY_LANG = {
  en: [
    {
      text: 'I have been able to laugh and see the funny side of things',
      options: [
        { label: 'As much as I always could', value: 0 },
        { label: 'Not quite so much now', value: 1 },
        { label: 'Definitely not so much now', value: 2 },
        { label: 'Not at all', value: 3 },
      ],
    },
    {
      text: 'I have looked forward with enjoyment to things',
      options: [
        { label: 'As much as I ever did', value: 0 },
        { label: 'Rather less than I used to', value: 1 },
        { label: 'Definitely less than I used to', value: 2 },
        { label: 'Hardly at all', value: 3 },
      ],
    },
    {
      text: 'I have blamed myself unnecessarily when things went wrong',
      options: [
        { label: 'No, never', value: 0 },
        { label: 'Not very often', value: 1 },
        { label: 'Yes, some of the time', value: 2 },
        { label: 'Yes, most of the time', value: 3 },
      ],
    },
    {
      text: 'I have been anxious or worried for no good reason',
      options: [
        { label: 'No, not at all', value: 0 },
        { label: 'Hardly ever', value: 1 },
        { label: 'Yes, sometimes', value: 2 },
        { label: 'Yes, very often', value: 3 },
      ],
    },
    {
      text: 'I have felt scared or panicky for no very good reason',
      options: [
        { label: 'No, not at all', value: 0 },
        { label: 'No, not much', value: 1 },
        { label: 'Yes, sometimes', value: 2 },
        { label: 'Yes, quite a lot', value: 3 },
      ],
    },
    {
      text: 'Things have been getting on top of me',
      options: [
        { label: 'No, I have been coping as well as ever', value: 0 },
        { label: 'No, most of the time I have coped quite well', value: 1 },
        { label: "Yes, sometimes I haven't been coping as well as usual", value: 2 },
        { label: "Yes, most of the time I haven't been able to cope at all", value: 3 },
      ],
    },
    {
      text: 'I have been so unhappy that I have had difficulty sleeping',
      options: [
        { label: 'No, not at all', value: 0 },
        { label: 'Not very often', value: 1 },
        { label: 'Yes, sometimes', value: 2 },
        { label: 'Yes, most of the time', value: 3 },
      ],
    },
    {
      text: 'I have felt sad or miserable',
      options: [
        { label: 'No, not at all', value: 0 },
        { label: 'Not very often', value: 1 },
        { label: 'Yes, quite often', value: 2 },
        { label: 'Yes, most of the time', value: 3 },
      ],
    },
    {
      text: 'I have been so unhappy that I have been crying',
      options: [
        { label: 'No, never', value: 0 },
        { label: 'Only occasionally', value: 1 },
        { label: 'Yes, quite often', value: 2 },
        { label: 'Yes, most of the time', value: 3 },
      ],
    },
    {
      text: 'The thought of harming myself has occurred to me',
      options: [
        { label: 'Never', value: 0 },
        { label: 'Hardly ever', value: 1 },
        { label: 'Sometimes', value: 2 },
        { label: 'Yes, quite often', value: 3 },
      ],
    },
  ],
  arz: [
    {
      text: 'استطعت أن أضحك وأن أرى الجانب المضحك في الأمور',
      options: [
        { label: 'مثل ما كنت دائماً', value: 0 },
        { label: 'ليس تماماً كما كنت', value: 1 },
        { label: 'بالتأكيد أقل بكثير الآن', value: 2 },
        { label: 'أبداً', value: 3 },
      ],
    },
    {
      text: 'تطلعت إلى الأشياء بمتعة',
      options: [
        { label: 'مثل ما كنت دائماً', value: 0 },
        { label: 'أقل مما اعتدت', value: 1 },
        { label: 'بالتأكيد أقل مما اعتدت', value: 2 },
        { label: 'نادراً جداً', value: 3 },
      ],
    },
    {
      text: 'لمت نفسي بلا داعٍ عندما تسوء الأمور',
      options: [
        { label: 'لا، أبداً', value: 0 },
        { label: 'ليس كثيراً', value: 1 },
        { label: 'نعم، بعض الوقت', value: 2 },
        { label: 'نعم، معظم الوقت', value: 3 },
      ],
    },
    {
      text: 'شعرت بالقلق أو التوتر دون سبب وجيه',
      options: [
        { label: 'لا، أبداً', value: 0 },
        { label: 'نادراً جداً', value: 1 },
        { label: 'نعم، أحياناً', value: 2 },
        { label: 'نعم، كثيراً جداً', value: 3 },
      ],
    },
    {
      text: 'شعرت بالخوف أو الهلع دون سبب وجيه',
      options: [
        { label: 'لا، أبداً', value: 0 },
        { label: 'لا، ليس كثيراً', value: 1 },
        { label: 'نعم، أحياناً', value: 2 },
        { label: 'نعم، كثيراً', value: 3 },
      ],
    },
    {
      text: 'الأمور تفوق طاقتي',
      options: [
        { label: 'لا، أتعامل كما كنت دائماً', value: 0 },
        { label: 'لا، معظم الوقت أتعامل بشكل جيد', value: 1 },
        { label: 'نعم، أحياناً لا أتعامل كما اعتدت', value: 2 },
        { label: 'نعم، معظم الوقت لم أستطع التعامل أبداً', value: 3 },
      ],
    },
    {
      text: 'كنت تعيسة لدرجة أنني وجدت صعوبة في النوم',
      options: [
        { label: 'لا، أبداً', value: 0 },
        { label: 'ليس كثيراً', value: 1 },
        { label: 'نعم، أحياناً', value: 2 },
        { label: 'نعم، معظم الوقت', value: 3 },
      ],
    },
    {
      text: 'شعرت بالحزن أو التعاسة',
      options: [
        { label: 'لا، أبداً', value: 0 },
        { label: 'ليس كثيراً', value: 1 },
        { label: 'نعم، كثيراً', value: 2 },
        { label: 'نعم، معظم الوقت', value: 3 },
      ],
    },
    {
      text: 'كنت تعيسة لدرجة أنني بكيت',
      options: [
        { label: 'لا، أبداً', value: 0 },
        { label: 'من حين لآخر فقط', value: 1 },
        { label: 'نعم، كثيراً', value: 2 },
        { label: 'نعم، معظم الوقت', value: 3 },
      ],
    },
    {
      text: 'راودتني فكرة إيذاء نفسي',
      options: [
        { label: 'أبداً', value: 0 },
        { label: 'نادراً جداً', value: 1 },
        { label: 'أحياناً', value: 2 },
        { label: 'نعم، كثيراً', value: 3 },
      ],
    },
  ],
}

export function phqSeverity(score, isAr) {
  if (score <= 4) {
    return {
      label: isAr ? 'طفيف' : 'Minimal',
      className: 'severity-minimal',
      meaning: isAr
        ? 'النتيجة دي بتوضح أعراض اكتئاب بسيطة أو شبه معدومة. المزاج الواطي أحيانًا بيحصل ومش شرط تحتاج تروح لدكتور.'
        : 'A score in this range suggests minimal or no significant depressive symptoms. Occasional low mood is common and does not necessarily require clinical intervention.',
    }
  }
  if (score <= 9) {
    return {
      label: isAr ? 'خفيف' : 'Mild',
      className: 'severity-mild',
      meaning: isAr
        ? 'النتيجة بتوضح أعراض اكتئاب خفيفة. راقب نفسك، نام كويس، واتسند على الناس اللي حواليك. لو فضل كده، كلم دكتور.'
        : 'A score in this range suggests mild depressive symptoms. Self-monitoring, healthy routines, and social support may help; consider a follow-up screen if symptoms persist or worsen.',
    }
  }
  if (score <= 14) {
    return {
      label: isAr ? 'متوسط' : 'Moderate',
      className: 'severity-moderate',
      meaning: isAr
        ? 'النتيجة بتوضح أعراض متوسطة ممكن تأثر على يومك. الأحسن تتكلم مع دكتور أو مختص.'
        : 'A score in this range suggests moderate depressive symptoms that may be affecting daily functioning. Discussing these results with a healthcare professional is recommended.',
    }
  }
  if (score <= 19) {
    return {
      label: isAr ? 'متوسط إلى شديد' : 'Moderately severe',
      className: 'severity-mod-severe',
      meaning: isAr
        ? 'النتيجة بتوضح أعراض أقرب للشدة. كلم مختص قريب عشان تشوف خيارات المساعدة.'
        : 'A score in this range suggests moderately severe depressive symptoms. A timely conversation with a healthcare professional is recommended to discuss treatment options.',
    }
  }
  return {
    label: isAr ? 'شديد' : 'Severe',
    className: 'severity-severe',
    meaning: isAr
      ? 'النتيجة بتوضح أعراض شديدة. كلم مختص في أقرب وقت عشان تقييم أوضح.'
      : 'A score in this range suggests severe depressive symptoms. It is strongly recommended that you speak with a healthcare professional soon for a fuller evaluation.',
  }
}

export function gadSeverity(score, isAr) {
  if (score <= 4) {
    return {
      label: isAr ? 'طفيف' : 'Minimal',
      className: 'severity-minimal',
      meaning: isAr
        ? 'النتيجة بتوضح قلق بسيط أو معدوم. القلق أحيانًا بيحصل ومش شرط يحتاج تدخل.'
        : 'A score in this range suggests minimal or no significant anxiety symptoms. Occasional worry is common and does not necessarily require clinical intervention.',
    }
  }
  if (score <= 9) {
    return {
      label: isAr ? 'خفيف' : 'Mild',
      className: 'severity-mild',
      meaning: isAr
        ? 'النتيجة بتوضح أعراض قلق خفيفة. راقب نفسك وحاول تهدي التوتر. لو فضل كده، كلم دكتور.'
        : 'A score in this range suggests mild anxiety symptoms. Self-monitoring and stress-management strategies may help; consider a follow-up screen if symptoms persist or worsen.',
    }
  }
  if (score <= 14) {
    return {
      label: isAr ? 'متوسط' : 'Moderate',
      className: 'severity-moderate',
      meaning: isAr
        ? 'النتيجة بتوضح قلق متوسط ممكن يأثر على يومك. الأحسن تتكلم مع مختص.'
        : 'A score in this range suggests moderate anxiety symptoms that may be starting to affect daily functioning. Discussing these results with a healthcare professional is recommended.',
    }
  }
  return {
    label: isAr ? 'شديد' : 'Severe',
    className: 'severity-severe',
    meaning: isAr
      ? 'النتيجة بتوضح قلق شديد. كلم مختص قريب.'
      : 'A score in this range suggests severe anxiety symptoms. It is strongly recommended that you speak with a healthcare professional soon for a fuller evaluation.',
  }
}

export function epdsSeverity(score, isAr) {
  if (score <= 8) {
    return {
      label: isAr ? 'احتمال منخفض' : 'Low likelihood',
      className: 'severity-minimal',
      meaning: isAr
        ? 'النتيجة بتوضح احتمال منخفض لاكتئاب ما بعد الولادة. التعب وتغيّر المزاج شائعين في الفترة دي.'
        : 'A score in this range suggests a low likelihood of postnatal depression. Occasional low mood or fatigue is common in the postpartum period.',
    }
  }
  if (score <= 11) {
    return {
      label: isAr ? 'ممكن — راقبي' : 'Possible — monitor',
      className: 'severity-mild',
      meaning: isAr
        ? 'في أعراض ممكن تكون موجودة. راقبي إحساسك وكلّمي طبيبة أو زائرة صحية لو استمرت.'
        : 'A score in this range suggests some depressive symptoms may be present. Monitoring how you feel over the next couple of weeks and talking with your midwife, health visitor, or GP is a reasonable next step.',
    }
  }
  if (score <= 13) {
    return {
      label: isAr ? 'احتمال واضح' : 'Fairly high likelihood',
      className: 'severity-moderate',
      meaning: isAr
        ? 'الاحتمال أوضح. الأحسن تتابعي مع مختص رعاية صحية.'
        : 'A score in this range suggests a fairly high likelihood of postnatal depression. A follow-up conversation with a healthcare professional is recommended.',
    }
  }
  return {
    label: isAr ? 'احتمال عالي' : 'High likelihood',
    className: 'severity-severe',
    meaning: isAr
      ? 'الاحتمال عالي. كلّمي مختص قريب عشان تقييم أوضح.'
      : 'A score in this range suggests a high likelihood of postnatal depression. It is strongly recommended that you speak with a healthcare professional soon for a fuller assessment.',
  }
}
