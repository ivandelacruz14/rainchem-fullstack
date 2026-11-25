import { Component } from "react";

/** Catches a render error so one broken section shows a clear message instead of a blank screen. */
export default class ErrorBox extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  componentDidCatch(error, info) {
    // Keep the details in the browser console for the developer.
    console.error("Display error:", error, info);
  }
  render() {
    if (this.state.error) {
      return (
        <div className="alert alert-error" role="alert">
          <strong>This part could not be displayed.</strong> Refresh the page. If it keeps happening, send this message to the developer: {String(this.state.error.message || this.state.error)}
        </div>
      );
    }
    return this.props.children;
  }
}
