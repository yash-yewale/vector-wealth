import json
from sentiment import compute_sentiment

text1 = "Reliance Industries Q3 profit jumps 15% on strong retail growth."
text2 = "TCS reports a massive drop in revenue, missing analyst estimates."
text3 = "HDFC Bank shares remain flat as earnings meet expectations."

print("Text 1:", compute_sentiment(text1))
print("Text 2:", compute_sentiment(text2))
print("Text 3:", compute_sentiment(text3))
