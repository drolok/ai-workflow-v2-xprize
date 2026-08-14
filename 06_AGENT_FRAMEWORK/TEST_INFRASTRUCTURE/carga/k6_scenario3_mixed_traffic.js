import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    mixed_traffic: {
      executor: 'per-vu-iterations',
      vus: 150,
      iterations: 1,
      maxDuration: '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<3500'],
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
  return { tokens };
}

export default function (data) {
  const token = data.tokens[__VU % data.tokens.length];
  const params = {
    headers: {
      'Authorization': 'Bearer ' + token
    }
  };

  const type = __VU % 3;
  let res;
  if (type === 0) {
    res = http.get(BASE_URL + '/tasks', params);
  } else if (type === 1) {
    res = http.get(BASE_URL + '/categories', params);
  } else {
    res = http.get(BASE_URL + '/auth/me', params);
  }

  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
