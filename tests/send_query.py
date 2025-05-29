import requests
import time

url = "http://127.0.0.1:8000/chat"

# # Step 1: Ask a math question
# data1 = {"message": "What is the sum of 2+2"}
# response1 = requests.post(url, json=data1)
# print("Response 1:", response1.json())

# # Optional pause for realism
# time.sleep(1)

# # Step 2: Ask a follow-up question — physics related
# data2 = {"message": "Now do the same for 3 what you did before for 2?"}
# response2 = requests.post(url, json=data2)
# print("Response 2:", response2.json())
# time.sleep(1)

# data3 = {"message": "What is the speed of light?"}
# response3 = requests.post(url, json=data3)
# print("Response 3:", response3.json())

time.sleep(1)
data4 = {"message": "Convert 1000 meters to kilometers."}
response4 = requests.post(url, json=data4)
print("Response 4:", response4.json())

# time.sleep(1)

# data5 = {"message": "What is the value of Planck's constant?"}
# response5 = requests.post(url, json=data5)
# print("Response 5:", response5.json())

# time.sleep(1)



