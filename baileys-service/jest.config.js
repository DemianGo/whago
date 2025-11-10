"use strict";

module.exports = {
  testEnvironment: "node",
  collectCoverage: true,
  collectCoverageFrom: ["src/**/*.js", "!src/index.js"],
  coverageDirectory: "coverage",
};

