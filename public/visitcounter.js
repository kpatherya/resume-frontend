const options = {
  method: 'POST',
  mode: 'cors',
  headers: {
    'Content-Type': 'application/json',
  }
};

const visitTarget = document.querySelector('span.visits');

if (visitTarget) {
  fetch('https://56uump58ii.execute-api.us-east-1.amazonaws.com/dev/', options)
    .then((response) => {
      if (response.ok) {
        return response.json();
      }
      throw new Error('Network Response Error');
    })
    .then((data) => {
      const count = typeof data === 'object'
        ? (data.count ?? data.visits ?? Object.values(data)[0] ?? 0)
        : data;
      visitTarget.textContent = count;
    })
    .catch((error) => {
      console.log('Error: ', error);
      visitTarget.textContent = '0';
    });
}