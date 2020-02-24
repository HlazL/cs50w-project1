import requests

res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "Qjf05UOoL8HmYBy5pBcg", "isbns": "9781632168146"})
print(res.json())
