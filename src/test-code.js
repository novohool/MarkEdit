// 这是一个测试JavaScript文件
function helloWorld() {
  console.log("Hello, World!");
  return true;
}

// 测试对象
const testObject = {
  name: "Test",
  value: 42,
  isActive: true,
  tags: ["javascript", "test", "code"]
};

// 测试类
class TestClass {
  constructor(name) {
    this.name = name;
  }
  
  greet() {
    return `Hello, ${this.name}!`;
  }
}

// 导出函数
export { helloWorld, testObject, TestClass };