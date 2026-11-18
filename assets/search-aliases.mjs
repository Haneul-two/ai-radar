// 검색 별칭: 같은 대상을 가리키는 한글·영어 이름 묶음. 순수 데이터 + 확장 함수.
// 새 주최·출처가 영어(또는 한글)로만 저장되면 여기에 한 줄 추가한다. 모두 소문자로 비교한다.
export const ALIAS_GROUPS = [
  ['upstage', '업스테이지'],
  ['moducon', '모두콘'],
  ['modulabs', '모두의연구소'],
  ['luma', '루마'],
  ['notion', '노션'],
  ['nvidia', '엔비디아'],
  ['google', '구글'],
  ['openai', '오픈ai', '오픈에이아이'],
  ['codex', '코덱스'],
  ['anthropic', '앤트로픽'],
  ['claude', '클로드'],
  ['gemini', '제미나이'],
  ['microsoft', '마이크로소프트'],
  ['amazon', 'aws', '아마존'],
  ['cursor', '커서'],
  ['samsung', '삼성'],
  ['naver', '네이버'],
  ['kakao', '카카오'],
  ['lotte', '롯데'],
  ['hashed', '해시드'],
  ['clickhouse', '클릭하우스'],
  ['neurips', '뉴립스'],
  ['devpost', '데브포스트'],
  ['wevity', '위비티'],
  ['linkareer', '링커리어'],
  ['gpters', '지피터스'],
  ['hackathon', '해커톤'],
  ['conference', '컨퍼런스', '콘퍼런스', '학회'],
  ['meetup', '밋업'],
  ['seminar', '세미나'],
  ['webinar', '웨비나'],
  ['seoul', '서울'],
];

// 검색어 한 단어 → 함께 찾을 단어 목록. 묶음의 이름을 2글자 이상으로 앞부분만 입력해도(예: '업스테') 묶음 전체로 넓힌다.
export function expandToken(token) {
  const out = new Set([token]);
  if (token.length < 2) return [...out];
  for (const group of ALIAS_GROUPS) {
    if (group.some((name) => name.startsWith(token))) group.forEach((name) => out.add(name));
  }
  return [...out];
}
