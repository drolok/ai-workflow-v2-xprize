import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    task_creation: {
      executor: 'per-vu-iterations',
      vus: 100,
      iterations: 1,
      maxDuration: '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<3000'],
  },
};

const BASE_URL = 'http://localhost:3001/api/v1';

export function setup() {
  const tokens = [];
  for (let i = 1; i <= 20; i++) {
    const email = 'user_test_official_' + i + '@test.pe';
    const res = http.post(BASE_URL + '/auth/login', JSON.stringify({
      email: email,
      password: 'Password123!'
    }), { headers: { 'Content-Type': 'application/json' } });

    if (res.status === 200) {
      const body = JSON.parse(res.body);
      tokens.push(body.data.accessToken);
    }
  }

  const catRes = http.get(BASE_URL + '/categories');
  const catBody = JSON.parse(catRes.body);
  const catList = catBody.data || catBody;
  const categoryId = catList.length > 0 ? catList[0].id : 'cat_general';

  return { tokens, categoryId };
}

export default function (data) {
  const token = data.tokens[__VU % data.tokens.length];
  const payload = JSON.stringify({
    title: 'k6 Concurrent Task #' + __VU,
    description: 'Task created during official k6 load test execution',
    categoryId: data.categoryId,
    basePrice: 25,
    district: 'Miraflores',
    address: 'Av. Larco 123'
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token,
    },
  };

  const res = http.post(BASE_URL + '/tasks', payload, params);

  check(res, {
    'status is 201': (r) => r.status === 201,
  });
}
