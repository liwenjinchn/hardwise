/** Compile-time guard against drift between backend-generated and handwritten contracts. */

import type * as Generated from "./generated/workbench-contracts";
import type * as Handwritten from "./types";

type Assignable<From, To> = [From] extends [To] ? true : false;
type Assert<T extends true> = T;

type _WorkbenchStateGeneratedToHandwritten = Assert<
  Assignable<Generated.WorkbenchState, Handwritten.WorkbenchState>
>;
type _WorkbenchStateHandwrittenToGenerated = Assert<
  Assignable<Handwritten.WorkbenchState, Generated.WorkbenchState>
>;
type _ComponentDetailGeneratedToHandwritten = Assert<
  Assignable<Generated.ComponentDetail, Handwritten.ComponentDetail>
>;
type _ComponentDetailHandwrittenToGenerated = Assert<
  Assignable<Handwritten.ComponentDetail, Generated.ComponentDetail>
>;
type _ImportResponseGeneratedToHandwritten = Assert<
  Assignable<Generated.ImportResponse, Handwritten.ImportResponse>
>;
type _ImportResponseHandwrittenToGenerated = Assert<
  Assignable<Handwritten.ImportResponse, Generated.ImportResponse>
>;
type _ChatRequestGeneratedToHandwritten = Assert<
  Assignable<Generated.ChatRequest, Handwritten.ChatRequest>
>;
type _ChatRequestHandwrittenToGenerated = Assert<
  Assignable<Handwritten.ChatRequest, Generated.ChatRequest>
>;
type _ChatResponseGeneratedToHandwritten = Assert<
  Assignable<Generated.ChatResponse, Handwritten.ChatResponse>
>;
type _ChatResponseHandwrittenToGenerated = Assert<
  Assignable<Handwritten.ChatResponse, Generated.ChatResponse>
>;
