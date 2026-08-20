/** Public guideline URLs keyed by PDF filename in pdfs/. Keep in sync with settings.py SOURCE_URLS. */
export const SOURCE_URLS = {
  'WHOEMMNH219E-eng.pdf':
    'https://iris.who.int/server/api/core/bitstreams/0ba3bb61-66f9-4926-abc3-60b0629f297e/content',
  'WHOEMMNH222E-eng.pdf':
    'https://iris.who.int/items/69cec305-c375-4832-91d4-bef1db8d5d26',
  'anxiety-adults-screening-final-recommendation.pdf':
    'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/anxiety-adults-screening',
  'depression-in-adults-pdf-58302785221.pdf':
    'https://www.nice.org.uk/guidance/qs8',
  'depression-in-adults-treatment-and-management-pdf-66143832307909.pdf':
    'https://www.nice.org.uk/guidance/ng222',
  'depression-in-adults-with-a-chronic-physical-health-problem-recognition-and-management-pdf-975744316357.pdf':
    'https://www.nice.org.uk/guidance/cg91',
  'depression-in-children-and-young-people-identification-and-management-pdf-66141719350981.pdf':
    'https://www.nice.org.uk/guidance/ng134',
  'depression-in-children-and-young-people-pdf-2098673428165.pdf':
    'https://www.nice.org.uk/guidance/qs48',
  'depression-suicide-risk-adults-rs.pdf':
    'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/screening-depression-suicide-risk-adults',
  'perinatal-depression-final-rec-statement.pdf':
    'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/perinatal-depression-preventive-interventions',
  'screening-anxiety-children-final-recommendation.pdf':
    'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/screening-anxiety-children-adolescents',
  'screening-depression-suicide-risk-children-final-recommendation.pdf':
    'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/screening-depression-suicide-risk-children-adolescents',
}

function lookupUrl(filename) {
  if (!filename) return null
  if (SOURCE_URLS[filename]) return SOURCE_URLS[filename]
  const lower = filename.toLowerCase()
  const exact = Object.entries(SOURCE_URLS).find(([key]) => key.toLowerCase() === lower)
  if (exact) return exact[1]

  const stem = lower.replace(/\.pdf$/i, '')
  let best = null
  let bestLen = 0
  for (const [key, url] of Object.entries(SOURCE_URLS)) {
    const keyStem = key.toLowerCase().replace(/\.pdf$/i, '')
    if (stem.includes(keyStem) || keyStem.includes(stem)) {
      if (keyStem.length > bestLen) {
        best = url
        bestLen = keyStem.length
      }
    }
  }
  return best
}

export function resolveSourceUrl(filename, page) {
  const url = lookupUrl(filename)
  if (!url) return null
  const pdfLike =
    url.toLowerCase().endsWith('.pdf') ||
    url.includes('/bitstreams/') ||
    url.toLowerCase().endsWith('/content')
  if (page && pdfLike) return `${url}#page=${page}`
  return url
}
