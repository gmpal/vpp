from src.optimization import optimize
from src.battery import Battery

if __name__ == "__main__":
    batteries = [Battery(i) for i in range(3)]
    df = optimize(batteries)
    print(df)
