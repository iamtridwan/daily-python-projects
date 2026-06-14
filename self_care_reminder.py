from random import choice

self_care_activities = [
    "Take a short walk in nature. 🌿",
    "Drink a big glass of water. 💧",
    "Do some deep breathing for 5 minutes. 🧘‍♂️",
    "Listen to your favorite music. 🎵",
    "Write down three things you're grateful for. ✨",
    "Read a chapter from a book you love. 📚",
    "Stretch your body gently. 🤸‍♀️",
    "Spend a few minutes with a pet or a loved one. 🐾",
    "Watch the sunset or sunrise. 🌅"
]


if __name__ == '__main__':
    print("Here is your self-care activity for today:")
    print('************************************')
    print(choice(self_care_activities))
    print('************************************')