import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';

export const winnersCount = new Counter('winners_200');
export const conflictsCount = new Counter('conflicts_409');

export const options = {
  scenarios: {
    race_condition: {
      executor: 'per-vu-iterations',
      vus: 50,
      iterations: 1,
      maxDuration: '30s',
    },
  },
};

const BASE_URL = 'http://localhost:3001/api/v1';

export function setup() {
  // Login pre-approved Client (user 1) & Pro (user 2)
  const clientLogin = http.post(BASE_URL + '/auth/login', JSON.stringify({ email: 'user_test_official_1@test.pe', password: 'Password123!' }), { headers: { 'Content-Type': 'application/json' } });
  const clientToken = JSON.parse(clientLogin.body).data.accessToken;

  const proLogin = http.post(BASE_URL + '/auth/login', JSON.stringify({ email: 'user_test_official_2@test.pe', password: 'Password123!' }), { headers: { 'Content-Type': 'application/json' } });
  const proToken = JSON.parse(proLogin.body).data.accessToken;

  const catRes = http.get(BASE_URL + '/categories');
  const categoryId = JSON.parse(catRes.body).data[0].id;

  // Create Task by Client
  const taskRes = http.post(BASE_URL + '/tasks', JSON.stringify({
    title: 'k6 Race Condition Target Task',
    description: 'Target task for simultaneous bid acceptance race condition test',
    categoryId: categoryId,
    basePrice: 25,
    district: 'Miraflores',
    address: 'Av. Larco 123'
  }), {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + clientToken
    }
  });

  const taskBody = JSON.parse(taskRes.body);
  if (!taskBody.data) {
    throw new Error('Task creation failed in setup: ' + taskRes.body);
  }
  const taskId = taskBody.data.id;

  // Create Bid by Pro
  const bidRes = http.post(BASE_URL + '/tasks/' + taskId + '/bids', JSON.stringify({
    proposedPrice: 25,
    message: 'k6 Bid for Race Condition Test'
  }), {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + proToken
    }
  });

  const bidBody = JSON.parse(bidRes.body);
  if (!bidBody.data) {
    throw new Error('Bid creation failed in setup: ' + bidRes.body);
  }
  const bidId = bidBody.data.id;

  return { clientToken, bidId };
}

export default function (data) {
  const res = http.post(BASE_URL + '/bids/' + data.bidId + '/accept', JSON.stringify({}), {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + data.clientToken
    }
  });

  if (res.status === 200 || res.status === 201) {
    winnersCount.add(1);
  } else if (res.status === 409) {
    conflictsCount.add(1);
  }

  check(res, {
    'status is 200 or 409': (r) => r.status === 200 || r.status === 409,
  });
}
