import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const cacheHit = new Rate('recipe_cache_hit_rate');
const base = __ENV.API_URL || 'http://localhost:8000';
const slug = __ENV.RECIPE_SLUG;
const query = encodeURIComponent(__ENV.SEARCH_QUERY || 'pho');

if (!slug) {
  throw new Error('Set RECIPE_SLUG to an existing published recipe slug.');
}

const paths = [
  '/api/v1/recipes?page=1&pageSize=12',
  `/api/v1/recipes/${encodeURIComponent(slug)}`,
  `/api/v1/recipes/search?q=${query}&page=1&pageSize=12`,
];

export const options = {
  setupTimeout: '2m',
  scenarios: {
    recipe_reads: {
      executor: 'constant-vus',
      vus: 100,
      duration: __ENV.DURATION || '2m',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(50)<=150', 'p(95)<=500', 'p(99)<=1000'],
    recipe_cache_hit_rate: ['rate>=0.80'],
  },
};

export function setup() {
  for (const path of paths) {
    const response = http.get(`${base}${path}`);
    if (response.status !== 200) {
      throw new Error(`Warm-up failed for ${path}: HTTP ${response.status}`);
    }
  }
  // The shared API policy allows 100 requests/minute per source IP. Let the
  // warm-up requests leave that window before the 100-user measurement starts.
  sleep(61);
}

export default function () {
  const path = paths[Math.floor(Math.random() * paths.length)];
  const response = http.get(`${base}${path}`, { tags: { recipe_path: path.split('?')[0] } });
  check(response, { 'recipe read succeeds': (result) => result.status === 200 });
  cacheHit.add(response.headers['X-Recipe-Cache'] === 'HIT');
  sleep(65);
}
