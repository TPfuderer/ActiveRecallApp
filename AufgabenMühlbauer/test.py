class User:
    def __init__(self, name):
        self.name = name

    @classmethod
    def guest(cls):
        return cls("Guest")

u1 = User("Alice")
u2 = User.guest()

print(u1.name)
print(u2.name)