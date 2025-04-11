from mcp.server.fastmcp import FastMCP

# 创建 MCP 服务器实例
mcp = FastMCP("Calculator Server")

@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers.
    
    Args:
        a: The first number
        b: The second number
    Returns:
        The sum of a and b
    """
    return a + b

@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a.
    
    Args:
        a: The first number
        b: The second number
    Returns:
        The difference of a and b
    """
    return a - b

@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers.
    
    Args:
        a: The first number
        b: The second number
    Returns:
        The product of a and b
    """
    return a * b

@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b.
    
    Args:
        a: The dividend
        b: The divisor
    Returns:
        The quotient of a and b
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

import math

@mcp.tool()
def power(base: float, exponent: float) -> float:
    """Calculate base raised to the power of exponent.
    
    Args:
        base: The base number
        exponent: The exponent
    Returns:
        base raised to the power of exponent
    """
    return base ** exponent

@mcp.tool()
def sqrt(x: float) -> float:
    """Calculate the square root of x.
    
    Args:
        x: The number to calculate the square root of
    Returns:
        The square root of x
    """
    if x < 0:
        raise ValueError("Cannot calculate square root of a negative number")
    return math.sqrt(x)

@mcp.tool()
def log(x: float, base: float = math.e) -> float:
    """Calculate the logarithm of x with the given base.
    
    Args:
        x: The number to calculate the logarithm of
        base: The base of the logarithm (default is e)
    Returns:
        The logarithm of x with the given base
    """
    if x <= 0:
        raise ValueError("Logarithm undefined for non-positive values")
    return math.log(x, base)

@mcp.tool()
def sin(x: float) -> float:
    """Calculate sine of x (in radians).
    
    Args:
        x: The angle in radians
    Returns:
        The sine of x
    """
    return math.sin(x)

@mcp.tool()
def cos(x: float) -> float:
    """Calculate cosine of x (in radians).
    
    Args:
        x: The angle in radians
    Returns:
        The cosine of x
    """
    return math.cos(x)

@mcp.tool()
def tan(x: float) -> float:
    """Calculate tangent of x (in radians).
    
    Args:
        x: The angle in radians
    Returns:
        The tangent of x
    """
    return math.tan(x)

import statistics

@mcp.tool()
def mean(numbers: list[float]) -> float:
    """Calculate the mean of a list of numbers.
    
    Args:
        numbers: List of numbers
    Returns:
        The mean of the numbers
    """
    return statistics.mean(numbers)

@mcp.tool()
def median(numbers: list[float]) -> float:
    """Calculate the median of a list of numbers.
    
    Args:
        numbers: List of numbers
    Returns:
        The median of the numbers
    """
    return statistics.median(numbers)

@mcp.tool()
def stdev(numbers: list[float]) -> float:
    """Calculate the standard deviation of a list of numbers.
    
    Args:
        numbers: List of numbers
    Returns:
        The standard deviation of the numbers
    """
    return statistics.stdev(numbers)

import numpy as np

@mcp.tool()
def matrix_multiply(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    """Multiply two matrices.
    
    Args:
        a: First matrix
        b: Second matrix
    Returns:
        The product of the two matrices
    """
    return np.dot(a, b).tolist()

@mcp.resource("constants://pi")
def get_pi() -> str:
    """Get the value of pi.
    
    Returns:
        The value of pi as a string
    """
    return str(math.pi)

from mcp.server.fastmcp.prompts import base

@mcp.prompt()
def calculate_expression(expression: str) -> str:
    """Prompt to calculate an expression."""
    return f"请计算以下表达式：{expression}"

@mcp.prompt()
def solve_equation_prompt(equation: str) -> list[base.Message]:
    """Prompt to solve an equation."""
    return [
        base.UserMessage(f"请解以下方程：{equation}"),
        base.AssistantMessage("我将尝试解这个方程。")
    ]

if __name__ == "__main__":
    print("MCP 计算器服务器已启动。")
    mcp.run()